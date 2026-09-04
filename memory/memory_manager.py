"""Public API for storing and retrieving Jarvis memories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .memory_models import MemoryRecord, MemoryType, normalize_memory_type
from .memory_retriever import MemoryRetriever
from .memory_store import MemoryStore


class MemoryManager:
    """Coordinate validation, SQLite storage, and ranked retrieval."""

    def __init__(
        self,
        database_path: str | Path | dict[str, Any] = "memory_database.sqlite",
        *,
        enabled: bool = True,
        max_results: int = 10,
        importance_threshold: float = 0.0,
    ) -> None:
        if isinstance(database_path, dict):
            configuration = database_path
            database_path = configuration.get(
                "database_path", "memory_database.sqlite"
            )
            enabled = configuration.get("enabled", enabled)
            max_results = configuration.get("max_results", max_results)
            importance_threshold = configuration.get(
                "importance_threshold", importance_threshold
            )
        max_results = int(max_results)
        if max_results < 1:
            raise ValueError("max_results must be at least 1.")
        self.enabled = bool(enabled)
        self.database_path = Path(database_path)
        self.max_results = max_results
        self.importance_threshold = self._validate_score(
            importance_threshold, "importance_threshold"
        )
        self.store = MemoryStore(self.database_path) if self.enabled else None
        self.retriever = MemoryRetriever(self.store) if self.store is not None else None

    def store_memory(
        self,
        memory_type: MemoryType | str,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance_score: float = 0.5,
    ) -> MemoryRecord | None:
        if not self.enabled:
            return None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Memory content must be a non-empty string.")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("Memory metadata must be a dictionary.")
        assert self.store is not None
        return self.store.create(
            normalize_memory_type(memory_type),
            content.strip(),
            dict(metadata or {}),
            self._validate_score(importance_score, "importance_score"),
        )

    def retrieve_memory(self, memory_id: str) -> MemoryRecord | None:
        if not self.enabled:
            return None
        assert self.store is not None
        return self.store.get(memory_id, touch=True)

    def update_memory(
        self,
        memory_id: str,
        *,
        memory_type: MemoryType | str | None = None,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None:
        if not self.enabled:
            return None
        changes: dict[str, Any] = {}
        if memory_type is not None:
            changes["memory_type"] = normalize_memory_type(memory_type)
        if content is not None:
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Memory content must be a non-empty string.")
            changes["content"] = content.strip()
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise TypeError("Memory metadata must be a dictionary.")
            changes["metadata"] = dict(metadata)
        if importance_score is not None:
            changes["importance_score"] = self._validate_score(
                importance_score, "importance_score"
            )
        assert self.store is not None
        return self.store.update(memory_id, changes)

    def delete_memory(self, memory_id: str) -> bool:
        if not self.enabled:
            return False
        assert self.store is not None
        return self.store.delete(memory_id)

    def search_memory(
        self,
        query: str,
        memory_type: MemoryType | str | None = None,
        *,
        max_results: int | None = None,
        importance_threshold: float | None = None,
    ) -> list[MemoryRecord]:
        if not self.enabled:
            return []
        result_limit = self.max_results if max_results is None else int(max_results)
        threshold = (
            self.importance_threshold
            if importance_threshold is None
            else self._validate_score(importance_threshold, "importance_threshold")
        )
        normalized_type = (
            normalize_memory_type(memory_type) if memory_type is not None else None
        )
        assert self.retriever is not None
        return self.retriever.search(
            query,
            memory_type=normalized_type,
            max_results=result_limit,
            importance_threshold=threshold,
        )

    def clear_session_memory(self) -> int:
        if not self.enabled:
            return 0
        assert self.store is not None
        return self.store.clear_type(MemoryType.SESSION_MEMORY.value)

    def close(self) -> None:
        if self.store is not None:
            self.store.close()

    def __enter__(self) -> "MemoryManager":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _validate_score(value: float, name: str) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError) as error:
            raise TypeError(f"{name} must be numeric.") from error
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0.")
        return score
