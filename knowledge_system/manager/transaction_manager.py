"""Consistency boundary for metadata, chunks, and Chroma vectors."""

from __future__ import annotations

import hashlib
import uuid
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from ..database import MetadataStore, VectorStore
from ..database.metadata_store import FAILED, PROCESSING, READY
from ..ingestion import DocumentChunker


class KnowledgeConsistencyError(RuntimeError):
    """Raised when metadata and vector state cannot be kept synchronized."""


def _synchronized(method: Callable[..., Any]) -> Callable[..., Any]:
    """Serialize operations that span both persistent stores."""

    @wraps(method)
    def wrapper(self: "KnowledgeTransactionManager", *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class KnowledgeTransactionManager:
    """Coordinate safe document operations across SQLite and Chroma."""

    def __init__(
        self,
        metadata_store: MetadataStore,
        vector_store: VectorStore,
        chunker: DocumentChunker,
    ) -> None:
        self.metadata_store = metadata_store
        self.vector_store = vector_store
        self.chunker = chunker
        self._lock = RLock()

    @staticmethod
    def calculate_document_hash(file_path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(file_path).open("rb") as source:
            while block := source.read(1024 * 1024):
                digest.update(block)
        return digest.hexdigest()

    @_synchronized
    def ingest_document(
        self,
        file_path: str | Path,
        loader: Callable[[str | Path], dict[str, Any]],
        *,
        tags: list[str] | tuple[str, ...] | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(file_path).expanduser().resolve()
        document_hash = self.calculate_document_hash(path)
        supplied_tags = tags if tags is not None else (metadata or {}).get("tags", [])
        if isinstance(supplied_tags, str):
            supplied_tags = [supplied_tags]
        claim_metadata = dict(metadata or {})
        claim_metadata.update(
            {
                "filename": path.name,
                "document_type": path.suffix.lower().lstrip("."),
                "tags": list(supplied_tags),
                "source": source or claim_metadata.get("source") or str(path),
                "document_hash": document_hash,
            }
        )
        document_id = str(uuid.uuid4())
        owner_token = str(uuid.uuid4())
        claim = self.metadata_store.claim_document(
            claim_metadata,
            document_hash=document_hash,
            owner_token=owner_token,
            document_id=document_id,
        )
        record = claim["record"]
        if not claim["owned"]:
            if claim["state"] == READY:
                if self._record_is_consistent(record):
                    return self._duplicate_result(record)
                if not self.metadata_store.reclaim_inconsistent_ready_document(
                    record["id"],
                    owner_token,
                ):
                    return self.ingest_document(
                        path,
                        loader,
                        tags=tags,
                        source=source,
                        metadata=metadata,
                    )
            else:
                return self._processing_result(record)

        document_id = record["id"]

        try:
            # A FAILED retry can retain partial vectors after an interrupted
            # process. The new owner always starts from an empty vector set.
            self.vector_store.delete_document_chunks(document_id)
            loaded = loader(path)
            if not loaded["content"].strip():
                raise ValueError(f"Document contains no extractable text: {path.name}")
            catalog_metadata = dict(loaded["metadata"])
            catalog_metadata.update(metadata or {})
            catalog_metadata.update(
                {
                    "filename": loaded["filename"],
                    "document_type": path.suffix.lower().lstrip("."),
                    "tags": list(supplied_tags),
                    "source": source or catalog_metadata.get("source") or str(path),
                    "document_hash": document_hash,
                }
            )
            if not self.metadata_store.update_owned_document(
                document_id,
                owner_token,
                catalog_metadata,
            ):
                raise KnowledgeConsistencyError(
                    f"Ingestion ownership was lost for document {document_id}."
                )
            chunks = self.chunker.split_document(
                loaded,
                parent_document=document_id,
            )
            if not self.metadata_store.update_owned_chunk_count(
                document_id,
                owner_token,
                len(chunks),
            ):
                raise KnowledgeConsistencyError(
                    f"Ingestion ownership was lost for document {document_id}."
                )
            chunk_metadatas = []
            for chunk in chunks:
                chunk_metadata = dict(catalog_metadata)
                chunk_metadata.update(chunk["metadata"])
                chunk_metadata["parent_document"] = document_id
                chunk_metadata["status"] = READY
                chunk_metadatas.append(chunk_metadata)
            self.vector_store.add_documents(
                [chunk["content"] for chunk in chunks],
                chunk_metadatas,
                document_ids=[chunk["chunk_id"] for chunk in chunks],
            )
            verification = self.verify_document(document_id)
            if not verification["consistent"]:
                raise KnowledgeConsistencyError(
                    f"Ingestion verification failed: {verification}"
                )
            if not self.metadata_store.finish_ingestion(
                document_id,
                owner_token,
                READY,
            ):
                raise KnowledgeConsistencyError(
                    f"Only the ingestion owner may mark {document_id} READY."
                )
        except Exception:
            self._rollback_ingestion(document_id, owner_token)
            raise

        stored_metadata = self.metadata_store.get_document(document_id)
        return {
            "id": document_id,
            "filename": loaded["filename"],
            "metadata": stored_metadata,
            "chunk_count": len(chunks),
            "chunks": [chunk["chunk_id"] for chunk in chunks],
            "duplicate": False,
            "status": READY,
        }

    def _rollback_ingestion(self, document_id: str, owner_token: str) -> None:
        vector_error: Exception | None = None
        try:
            self.vector_store.delete_document_chunks(document_id)
        except Exception as error:
            vector_error = error
        state_updated = self.metadata_store.finish_ingestion(
            document_id,
            owner_token,
            FAILED,
        )
        if not state_updated:
            raise KnowledgeConsistencyError(
                f"Could not mark failed ingestion {document_id} as FAILED."
            )
        if vector_error is not None:
            raise KnowledgeConsistencyError(
                f"Vector rollback failed for document {document_id}."
            ) from vector_error

    @_synchronized
    def delete_document(self, document_id: str) -> bool:
        record = self.metadata_store.get_document(document_id)
        chunks = self.vector_store.get_document_chunks(document_id)
        if record is None:
            self.vector_store.delete_chunks([chunk["id"] for chunk in chunks])
            return bool(chunks)

        self.metadata_store.update_document_state(document_id, status="deleting")
        try:
            self.vector_store.delete_document_chunks(document_id)
        except Exception:
            self.metadata_store.update_document_state(document_id, status=READY)
            raise
        try:
            deleted = self.metadata_store.delete_document(document_id)
            if not deleted:
                raise KnowledgeConsistencyError(
                    f"Metadata disappeared while deleting document {document_id}."
                )
        except Exception:
            try:
                self.vector_store.add_documents(
                    [chunk["content"] for chunk in chunks],
                    [chunk["metadata"] for chunk in chunks],
                    document_ids=[chunk["id"] for chunk in chunks],
                )
                self.metadata_store.update_document_state(document_id, status=READY)
            except Exception as rollback_error:
                raise KnowledgeConsistencyError(
                    f"Delete rollback failed for document {document_id}."
                ) from rollback_error
            raise

        verification = self.verify_document(document_id)
        if verification["metadata_exists"] or verification["actual_chunks"]:
            raise KnowledgeConsistencyError(
                f"Delete verification failed: {verification}"
            )
        return True

    def verify_document(self, document_id: str) -> dict[str, Any]:
        record = self.metadata_store.get_document(document_id)
        actual_chunks = self.vector_store.count_document_chunks(document_id)
        expected_chunks = int(record["chunk_count"]) if record is not None else 0
        return {
            "document_id": document_id,
            "metadata_exists": record is not None,
            "expected_chunks": expected_chunks,
            "actual_chunks": actual_chunks,
            "consistent": record is not None and expected_chunks == actual_chunks,
        }

    @_synchronized
    def reconcile(self, *, repair: bool = True) -> dict[str, Any]:
        records = {record["id"]: record for record in self.metadata_store.list_documents()}
        chunks_by_parent: dict[str, list[dict[str, Any]]] = {}
        for chunk in self.vector_store.get_all():
            parent = str(chunk["metadata"].get("parent_document") or chunk["id"])
            chunks_by_parent.setdefault(parent, []).append(chunk)

        orphan_chunk_ids = [
            chunk["id"]
            for parent, chunks in chunks_by_parent.items()
            if parent not in records
            for chunk in chunks
        ]
        incomplete_document_ids: list[str] = []
        recovered_document_ids: list[str] = []
        failed_with_chunks: set[str] = set()
        for document_id, record in records.items():
            actual = len(chunks_by_parent.get(document_id, []))
            expected = int(record["chunk_count"])
            state = str(record["status"]).upper()
            if state in {"PENDING", PROCESSING}:
                continue
            if state == FAILED:
                if actual:
                    incomplete_document_ids.append(document_id)
                    failed_with_chunks.add(document_id)
                continue
            if expected != actual or actual == 0:
                incomplete_document_ids.append(document_id)
            elif state != READY:
                recovered_document_ids.append(document_id)

        if repair:
            self.vector_store.delete_chunks(orphan_chunk_ids)
            for document_id in incomplete_document_ids:
                self.vector_store.delete_document_chunks(document_id)
                if document_id not in failed_with_chunks:
                    self.metadata_store.delete_document(document_id)
            for document_id in recovered_document_ids:
                self.metadata_store.update_document_state(document_id, status=READY)

        return {
            "orphan_chunks": orphan_chunk_ids,
            "incomplete_documents": incomplete_document_ids,
            "recovered_documents": recovered_document_ids,
            "repaired": repair,
        }

    def _record_is_consistent(self, record: dict[str, Any]) -> bool:
        verification = self.verify_document(record["id"])
        return bool(
            record.get("status") == READY
            and verification["consistent"]
            and verification["actual_chunks"] > 0
        )

    @staticmethod
    def _duplicate_result(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "filename": record["filename"],
            "metadata": record,
            "chunk_count": int(record["chunk_count"]),
            "chunks": [],
            "duplicate": True,
            "status": READY,
        }

    @staticmethod
    def _processing_result(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "filename": record["filename"],
            "metadata": record,
            "chunk_count": int(record["chunk_count"]),
            "chunks": [],
            "duplicate": True,
            "processing": True,
            "status": PROCESSING,
        }
