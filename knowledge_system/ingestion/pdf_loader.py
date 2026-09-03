"""Load text and document metadata from PDF files with pypdf."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader


def _pdf_metadata_value(metadata: Any, name: str) -> str | None:
    value = getattr(metadata, name, None) if metadata is not None else None
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


class PDFLoader:
    """Extract searchable text and useful metadata from a PDF document."""

    @staticmethod
    def load(file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"PDF document not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf document, received: {path.name}")

        reader = PdfReader(str(path))
        content = "\n\n".join(
            text.strip()
            for page in reader.pages
            if (text := (page.extract_text() or "")).strip()
        )
        document_metadata = reader.metadata
        metadata: dict[str, Any] = {
            "document_type": "pdf",
            "page_count": len(reader.pages),
        }
        for key in ("author", "title", "subject", "creator", "producer"):
            if value := _pdf_metadata_value(document_metadata, key):
                metadata[key] = value

        return {
            "filename": path.name,
            "content": content,
            "metadata": metadata,
        }


def load_pdf(file_path: str | Path) -> dict[str, Any]:
    """Functional interface for :class:`PDFLoader`."""

    return PDFLoader.load(file_path)
