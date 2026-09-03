"""High-level chunk retrieval with authoritative document metadata."""

from __future__ import annotations

from typing import Any

from ..database import MetadataStore, VectorStore


class SearchEngine:
    """Query chunk vectors and enrich matches from the metadata catalog."""

    def __init__(
        self,
        vector_store: VectorStore,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.metadata_store = metadata_store

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        results = self.vector_store.search(query, top_k=top_k)
        if self.metadata_store is None:
            return results
        ready_results: list[dict[str, Any]] = []
        for result in results:
            parent_id = result["metadata"].get("parent_document")
            if parent_id:
                catalog_metadata = self.metadata_store.get_document(parent_id)
                if (
                    catalog_metadata is not None
                    and catalog_metadata.get("status") == "READY"
                ):
                    result["metadata"].update(catalog_metadata)
                    result["metadata"]["parent_document"] = parent_id
                    ready_results.append(result)
        return ready_results
