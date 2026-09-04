"""Load UTF text documents using Python's native file support."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TextLoader:
    """Read a plain-text document without an external parser."""

    @staticmethod
    def load(
        file_path: str | Path,
        encoding: str = "utf-8-sig",
    ) -> dict[str, Any]:
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Text document not found: {path}")
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Expected a .txt document, received: {path.name}")

        return {
            "filename": path.name,
            "content": path.read_text(encoding=encoding),
            "metadata": {
                "document_type": "txt",
                "encoding": encoding,
            },
        }


def load_text(
    file_path: str | Path,
    encoding: str = "utf-8-sig",
) -> dict[str, Any]:
    """Functional interface for :class:`TextLoader`."""

    return TextLoader.load(file_path, encoding=encoding)
