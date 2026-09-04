"""Typed models shared by the Stone 6 memory subsystem."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    """Supported scopes and purposes for persistent memories."""

    SESSION_MEMORY = "session_memory"
    PROJECT_MEMORY = "project_memory"
    USER_PREFERENCE_MEMORY = "user_preference_memory"
    DECISION_MEMORY = "decision_memory"
    EXPERIENCE_MEMORY = "experience_memory"


MEMORY_TYPES = frozenset(item.value for item in MemoryType)


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


def normalize_memory_type(memory_type: MemoryType | str) -> str:
    """Return a validated string value for *memory_type*."""

    value = memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
    if value not in MEMORY_TYPES:
        raise ValueError(
            f"Unsupported memory type {value!r}; expected one of {sorted(MEMORY_TYPES)}."
        )
    return value


@dataclass(frozen=True)
class MemoryRecord:
    """One stored memory plus optional retrieval scores."""

    memory_id: str
    memory_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.5
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_accessed: datetime = field(default_factory=utc_now)
    access_count: int = 0
    relevance_score: float | None = None
    ranking_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-friendly representation."""

        data = asdict(self)
        for key in ("created_at", "updated_at", "last_accessed"):
            data[key] = data[key].isoformat()
        return data

    def __getitem__(self, key: str) -> Any:
        """Allow light-weight mapping access for compatibility-oriented callers."""

        return getattr(self, key)


# Concise compatibility name for callers that model one record as ``Memory``.
Memory = MemoryRecord
