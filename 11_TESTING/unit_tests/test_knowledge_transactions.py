from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from threading import Event

import pytest

from knowledge_system import KnowledgeManager
from knowledge_system.database import LocalHashEmbedder


class FailingEmbedder(LocalHashEmbedder):
    def embed(self, texts):
        raise RuntimeError("simulated embedding failure")


class BlockingEmbedder(LocalHashEmbedder):
    def __init__(self, started: Event, release: Event):
        super().__init__()
        self.started = started
        self.release = release

    def embed(self, texts):
        self.started.set()
        if not self.release.wait(timeout=10):
            raise RuntimeError("timed out waiting to release embedding")
        return super().embed(texts)


class BlockingFailEmbedder(BlockingEmbedder):
    def embed(self, texts):
        self.started.set()
        if not self.release.wait(timeout=10):
            raise RuntimeError("timed out waiting to release embedding")
        raise RuntimeError("simulated concurrent embedding failure")


def test_duplicate_ingestion_and_delete_synchronization(tmp_path: Path):
    source = tmp_path / "paper.txt"
    source.write_text("A unique research document about adaptive learning.", encoding="utf-8")
    manager = KnowledgeManager(tmp_path / "knowledge", chunk_size=30, chunk_overlap=5)

    first = manager.ingest_document(source)
    vector_count = manager.vector_store.count()
    duplicate = manager.ingest_document(source)

    assert duplicate["duplicate"] is True
    assert duplicate["id"] == first["id"]
    assert manager.metadata_store.count() == 1
    assert manager.vector_store.count() == vector_count

    assert manager.delete_document(first["id"]) is True
    assert manager.metadata_store.get_document(first["id"]) is None
    assert manager.vector_store.count_document_chunks(first["id"]) == 0
    assert manager.search("adaptive learning") == []
    manager.close()


def test_inconsistent_ready_document_is_atomically_rebuilt(tmp_path: Path):
    source = tmp_path / "rebuild.txt"
    source.write_text("Rebuild missing research vectors safely.", encoding="utf-8")
    manager = KnowledgeManager(tmp_path / "knowledge")
    original = manager.ingest_document(source)
    manager.vector_store.delete_document_chunks(original["id"])

    rebuilt = manager.ingest_document(source)

    assert rebuilt["id"] == original["id"]
    assert rebuilt["duplicate"] is False
    assert rebuilt["status"] == "READY"
    assert manager.transactions.verify_document(rebuilt["id"])["consistent"] is True
    manager.close()


def test_failed_ingestion_rolls_back_both_stores(tmp_path: Path):
    source = tmp_path / "failure.txt"
    source.write_text("This ingestion must fail safely.", encoding="utf-8")
    manager = KnowledgeManager(
        tmp_path / "knowledge",
        embedder=FailingEmbedder(),
    )

    with pytest.raises(RuntimeError, match="simulated embedding failure"):
        manager.ingest_document(source)

    failed = manager.metadata_store.list_documents()
    assert len(failed) == 1
    assert failed[0]["status"] == "FAILED"
    assert manager.vector_store.count() == 0

    manager.vector_store.embedder = LocalHashEmbedder()
    retry = manager.ingest_document(source)
    assert retry["status"] == "READY"
    assert retry["id"] == failed[0]["id"]
    assert manager.metadata_store.count() == 1
    assert manager.vector_store.count() == retry["chunk_count"]
    manager.close()


def test_independent_managers_atomically_claim_same_document(tmp_path: Path):
    source = tmp_path / "simultaneous.txt"
    source.write_text(
        "Two managers must not both own this research document.",
        encoding="utf-8",
    )
    started = Event()
    release = Event()
    storage = tmp_path / "knowledge"
    first = KnowledgeManager(storage, embedder=BlockingEmbedder(started, release))
    second = KnowledgeManager(storage, embedder=BlockingEmbedder(started, release))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(first.ingest_document, source),
            executor.submit(second.ingest_document, source),
        ]
        assert started.wait(timeout=10)
        completed, pending = wait(
            futures,
            timeout=10,
            return_when=FIRST_COMPLETED,
        )
        assert len(completed) == 1
        processing = next(iter(completed)).result()
        assert processing["status"] == "PROCESSING"
        assert processing["processing"] is True
        assert processing["duplicate"] is True

        release.set()
        ready = next(iter(pending)).result(timeout=10)

    assert ready["status"] == "READY"
    assert ready["duplicate"] is False
    assert ready["id"] == processing["id"]
    assert first.metadata_store.count() == 1
    assert first.metadata_store.get_document(ready["id"])["status"] == "READY"
    assert first.vector_store.count_document_chunks(ready["id"]) == ready["chunk_count"]
    assert first.transactions.verify_document(ready["id"])["consistent"] is True
    first.close()
    second.close()


def test_concurrent_owner_failure_never_reports_false_success(tmp_path: Path):
    source = tmp_path / "failing-simultaneous.txt"
    source.write_text("The owning ingestion will fail safely.", encoding="utf-8")
    started = Event()
    release = Event()
    storage = tmp_path / "knowledge"
    first = KnowledgeManager(
        storage,
        embedder=BlockingFailEmbedder(started, release),
    )
    second = KnowledgeManager(
        storage,
        embedder=BlockingFailEmbedder(started, release),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(first.ingest_document, source),
            executor.submit(second.ingest_document, source),
        ]
        assert started.wait(timeout=10)
        completed, pending = wait(
            futures,
            timeout=10,
            return_when=FIRST_COMPLETED,
        )
        processing = next(iter(completed)).result()
        assert processing["status"] == "PROCESSING"
        assert processing["duplicate"] is True

        release.set()
        with pytest.raises(RuntimeError, match="simulated concurrent embedding failure"):
            next(iter(pending)).result(timeout=10)

    failed = first.metadata_store.get_document(processing["id"])
    assert failed is not None
    assert failed["status"] == "FAILED"
    assert first.vector_store.count_document_chunks(processing["id"]) == 0

    second.vector_store.embedder = LocalHashEmbedder()
    retry = second.ingest_document(source)
    assert retry["status"] == "READY"
    assert retry["id"] == processing["id"]
    assert second.transactions.verify_document(retry["id"])["consistent"] is True
    first.close()
    second.close()


def test_reconciliation_removes_orphan_chunks(tmp_path: Path):
    manager = KnowledgeManager(tmp_path / "knowledge")
    manager.vector_store.add_document(
        "orphaned content",
        {"parent_document": "missing-document", "chunk_id": "orphan-chunk"},
        document_id="orphan-chunk",
    )

    report = manager.reconcile()

    assert report["orphan_chunks"] == ["orphan-chunk"]
    assert manager.vector_store.count() == 0
    manager.close()
