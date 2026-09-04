"""Shared typed state models for the Stone 5 reasoning layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """Lifecycle states for a planned task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class ExecutionStrategy:
    """Deterministic interpretation of a user request."""

    task_type: str
    complexity: str
    steps: list[str]
    required_agents: list[str]
    required_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-friendly representation."""

        return asdict(self)


@dataclass
class PlannedTask:
    """One executable unit in a workflow plan."""

    id: str
    description: str
    required_agent: str
    dependencies: list[str] = field(default_factory=list)
    result: Any = None
    status: TaskStatus = TaskStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        """Return task data with the enum represented as a string."""

        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class WorkflowState:
    """Mutable execution state for one workflow."""

    workflow_id: str
    current_task: str | None = None
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    skipped_tasks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-friendly workflow snapshot."""

        return asdict(self)


@dataclass
class EvaluationResult:
    """Quality assessment and actionable feedback for an output."""

    score: int
    issues: list[str]
    recommendation: str
    dimensions: dict[str, int]
    reviewer_result: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-friendly assessment."""

        return asdict(self)
