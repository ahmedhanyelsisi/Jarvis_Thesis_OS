"""Typed, serialization-friendly models for the cognitive dashboard."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    """Return an aware UTC timestamp for UI telemetry."""

    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class UIEvent:
    """One immutable event published by the cognitive UI layer."""

    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    source: str = "cognitive_ui"
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        # ``data`` is the Stone 8.0 name; payload is the durable event contract.
        if self.payload is None:
            object.__setattr__(self, "payload", dict(self.data))
        elif not self.data:
            object.__setattr__(self, "data", dict(self.payload))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class AgentStatus:
    """UI projection of an agent observed in a kernel response."""

    name: str
    status: str = "idle"
    current_task: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("started_at", "completed_at"):
            value = data[key]
            if value is not None:
                data[key] = value.isoformat()
        return data


@dataclass
class WorkflowStatus:
    """Current workflow state shown by the command center."""

    status: str = "idle"
    workflow_id: str | None = None
    current_task: str | None = None
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    skipped_tasks: list[str] = field(default_factory=list)
    total_tasks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SystemStatus:
    """Stable status contract shared by the kernel and future dashboards."""

    kernel: str
    agents: int
    memory: str
    voice: str
    workflow: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
