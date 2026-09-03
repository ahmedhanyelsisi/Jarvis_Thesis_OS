"""Public orchestration interface for Jarvis research knowledge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..database import Embedder, MetadataStore, VectorStore
from ..ingestion import DocumentChunker, load_docx, load_pdf, load_text
from ..memory import ResearchMemory
from ..retrieval import SearchEngine
from .transaction_manager import KnowledgeTransactionManager


class KnowledgeManager:
    """Ingest, retrieve, delete, reconcile, and remember research knowledge."""

    LOADERS = {
        ".pdf": load_pdf,
        ".docx": load_docx,
        ".txt": load_text,
    }

    def __init__(
        self,
        storage_path: str | Path | None = None,
        *,
        collection_name: str = "jarvis_knowledge",
        embedder: Embedder | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        default_storage = (
            Path(__file__).resolve().parents[2] / "04_KNOWLEDGE_SYSTEM" / "data"
        )
        self.storage_path = Path(storage_path or default_storage).expanduser().resolve()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.vector_store = VectorStore(
            self.storage_path / "chroma",
            collection_name=collection_name,
            embedder=embedder,
            embedding_config_path=self.storage_path / "embedding_config.json",
        )
        self.metadata_store = MetadataStore(self.storage_path / "metadata.sqlite3")
        self.memory = ResearchMemory(self.storage_path / "research_memory.sqlite3")
        self.chunker = DocumentChunker(chunk_size, chunk_overlap)
        self.search_engine = SearchEngine(self.vector_store, self.metadata_store)
        self.transactions = KnowledgeTransactionManager(
            self.metadata_store,
            self.vector_store,
            self.chunker,
        )

    def ingest_document(
        self,
        file_path: str | Path,
        *,
        tags: list[str] | tuple[str, ...] | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(file_path).expanduser().resolve()
        loader = self.LOADERS.get(path.suffix.lower())
        if loader is None:
            supported = ", ".join(sorted(self.LOADERS))
            raise ValueError(f"Unsupported document type. Supported types: {supported}")
        return self.transactions.ingest_document(
            path,
            loader,
            tags=tags,
            source=source,
            metadata=metadata,
        )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self.search_engine.search(query, top_k=top_k)

    def delete_document(self, document_id: str) -> bool:
        return self.transactions.delete_document(document_id)

    def reconcile(self, *, repair: bool = True) -> dict[str, Any]:
        return self.transactions.reconcile(repair=repair)

    def close(self) -> None:
        self.metadata_store.close()
        self.memory.close()

    def __enter__(self) -> "KnowledgeManager":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
