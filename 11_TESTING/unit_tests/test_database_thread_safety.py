from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from knowledge_system import KnowledgeManager
from knowledge_system.database import MetadataStore
from knowledge_system.memory import ResearchMemory


def test_repeated_database_operations_are_thread_safe(tmp_path: Path):
    metadata_path = tmp_path / "metadata.sqlite3"
    memory_path = tmp_path / "memory.sqlite3"
    metadata = MetadataStore(metadata_path)
    memory = ResearchMemory(memory_path)

    def store_record(index: int) -> None:
        document_id = metadata.add_document(
            {
                "filename": f"paper-{index}.txt",
                "document_type": "txt",
                "document_hash": f"hash-{index}",
            }
        )
        assert metadata.get_document(document_id) is not None
        memory.remember_topic(f"topic-{index}", {"index": index})

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(store_record, range(30)))

    assert metadata.count() == 30
    assert len(memory.get_memory("topic")) == 30
    metadata.close()
    memory.close()

    reopened_metadata = MetadataStore(metadata_path)
    reopened_memory = ResearchMemory(memory_path)
    assert reopened_metadata.count() == 30
    assert len(reopened_memory.get_memory("topic")) == 30
    reopened_metadata.close()
    reopened_memory.close()


def test_shared_knowledge_manager_supports_parallel_operations(tmp_path: Path):
    manager = KnowledgeManager(
        tmp_path / "knowledge",
        chunk_size=80,
        chunk_overlap=10,
    )
    sources = []
    for index in range(12):
        source = tmp_path / f"source-{index}.txt"
        source.write_text(
            f"Parallel research document {index} about adaptive education systems.",
            encoding="utf-8",
        )
        sources.append(source)

    with ThreadPoolExecutor(max_workers=6) as executor:
        ingested = list(executor.map(manager.ingest_document, sources))
        result_sets = list(
            executor.map(
                manager.search,
                ["adaptive education"] * 12,
            )
        )

    assert len({result["id"] for result in ingested}) == 12
    assert manager.metadata_store.count() == 12
    assert all(results for results in result_sets)
    assert all(
        result["metadata"]["status"] == "READY"
        for results in result_sets
        for result in results
    )
    manager.close()
