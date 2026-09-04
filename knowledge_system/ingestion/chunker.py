"""Character-based document chunking with overlap and source provenance."""

from __future__ import annotations

import uuid
from typing import Any


class DocumentChunker:
    """Split normalized loader output into overlapping searchable chunks."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1.")
        if overlap < 0:
            raise ValueError("overlap cannot be negative.")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_document(
        self,
        document: dict[str, Any],
        *,
        parent_document: str | None = None,
    ) -> list[dict[str, Any]]:
        """Split one loader result while retaining its metadata on every chunk."""

        content = document.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Document content cannot be empty.")

        parent_id = parent_document or str(uuid.uuid4())
        base_metadata = dict(document.get("metadata") or {})
        base_metadata["filename"] = str(document.get("filename") or "")
        chunks: list[dict[str, Any]] = []
        start = 0
        index = 0

        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            chunk_content = content[start:end]
            chunk_id = f"{parent_id}:chunk:{index:06d}"
            chunk_metadata = {
                **base_metadata,
                "chunk_id": chunk_id,
                "chunk_index": index,
                "parent_document": parent_id,
                "start_character": start,
                "end_character": end,
            }
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "parent_document": parent_id,
                    "content": chunk_content,
                    "metadata": chunk_metadata,
                }
            )
            if end == len(content):
                break
            start = end - self.overlap
            index += 1

        return chunks


def chunk_document(
    document: dict[str, Any],
    *,
    parent_document: str | None = None,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[dict[str, Any]]:
    """Functional interface for :class:`DocumentChunker`."""

    return DocumentChunker(chunk_size, overlap).split_document(
        document,
        parent_document=parent_document,
    )
