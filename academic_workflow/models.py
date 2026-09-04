"""Frozen data models for the Stone 12 Academic Workflow Orchestration Layer.

Stone 12 owns workflow state representation only.
The Kernel owns all execution decisions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


# ── Enums ─────────────────────────────────────────────────────


class ThesisStage(str, Enum):
    """Lifecycle stage for a thesis chapter."""

    PLANNING = "planning"
    DRAFTING = "drafting"
    ANALYSIS = "analysis"
    REVISION = "revision"
    REVIEW = "review"
    FINALIZATION = "finalization"
    COMPLETE = "complete"


class ActionPriority(str, Enum):
    """Deterministic priority levels for remediation actions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionCategory(str, Enum):
    """Source classification for action items."""

    CITATION = "citation"
    CONSISTENCY = "consistency"
    STRUCTURE = "structure"
    WRITING = "writing"
    RESEARCH_GAP = "research_gap"
    REVIEW = "review"


class PipelineStepStatus(str, Enum):
    """Outcome of a single workflow step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"


# Explicit rank for deterministic sorting (lower = more urgent).
PRIORITY_RANK: dict[ActionPriority, int] = {
    ActionPriority.CRITICAL: 0,
    ActionPriority.HIGH: 1,
    ActionPriority.MEDIUM: 2,
    ActionPriority.LOW: 3,
}


# ── Lifecycle Models ──────────────────────────────────────────


@dataclass(frozen=True)
class StageTransition:
    """Record of a single lifecycle stage change."""

    from_stage: ThesisStage
    to_stage: ThesisStage
    timestamp: datetime
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ChapterLifecycle:
    """Current lifecycle state plus transition history for one chapter."""

    chapter: str
    stage: ThesisStage
    history: tuple[StageTransition, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.chapter, str) or not self.chapter.strip():
            raise ValueError("Chapter name must be a non-empty string.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter": self.chapter,
            "stage": self.stage.value,
            "history": [t.to_dict() for t in self.history],
        }


# ── Action Models ─────────────────────────────────────────────


@dataclass(frozen=True)
class ActionItem:
    """One prioritized remediation action derived from Stone 9–11 findings.

    Priority is assigned exclusively by finding-type-to-severity mapping.
    No AI scoring. No heuristics.
    """

    priority: ActionPriority
    category: ActionCategory
    action_id: str
    description: str
    source_stone: int
    chapter: str | None = None
    location: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.priority, ActionPriority):
            raise TypeError("priority must be an ActionPriority")
        if not isinstance(self.category, ActionCategory):
            raise TypeError("category must be an ActionCategory")
        if not isinstance(self.source_stone, int):
            raise TypeError("source_stone must be an integer")
        if self.source_stone not in (9, 10, 11):
            raise ValueError("source_stone must be 9, 10, or 11.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority.value,
            "category": self.category.value,
            "action_id": self.action_id,
            "description": self.description,
            "source_stone": self.source_stone,
            "chapter": self.chapter,
            "location": self.location,
        }


@dataclass(frozen=True)
class ActionQueue:
    """Prioritized, deduplicated collection of remediation actions."""

    items: tuple[ActionItem, ...] = ()
    generated_at: datetime = field(default_factory=utc_now)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.items if i.priority == ActionPriority.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.items if i.priority == ActionPriority.HIGH)

    @property
    def total(self) -> int:
        return len(self.items)

    def by_chapter(self, chapter: str) -> tuple[ActionItem, ...]:
        return tuple(i for i in self.items if i.chapter == chapter)

    def by_category(self, category: ActionCategory) -> tuple[ActionItem, ...]:
        return tuple(i for i in self.items if i.category == category)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "generated_at": self.generated_at.isoformat(),
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "total": self.total,
        }


# ── Workflow Step Models ──────────────────────────────────────


@dataclass(frozen=True)
class PipelineStep:
    """Result of one analysis step in the workflow."""

    name: str
    status: PipelineStepStatus
    findings_count: int
    source_stone: int
    data: Any = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "findings_count": self.findings_count,
            "source_stone": self.source_stone,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class PipelineResult:
    """Collected output from all workflow steps."""

    pipeline_id: str
    steps: tuple[PipelineStep, ...]
    chapter: str | None
    started_at: datetime
    completed_at: datetime

    @property
    def total_findings(self) -> int:
        return sum(step.findings_count for step in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "steps": [s.to_dict() for s in self.steps],
            "chapter": self.chapter,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "total_findings": self.total_findings,
        }


# ── Milestone Models ──────────────────────────────────────────


@dataclass(frozen=True, order=True)
class Milestone:
    """One trackable thesis milestone."""

    chapter: str
    stage: ThesisStage
    sections_total: int
    sections_completed: int

    def __post_init__(self) -> None:
        if self.sections_total < 0:
            raise ValueError("sections_total must be non-negative.")
        if self.sections_completed < 0:
            raise ValueError("sections_completed must be non-negative.")
        if self.sections_completed > self.sections_total:
            raise ValueError(
                "sections_completed cannot exceed sections_total."
            )

    @property
    def completion_ratio(self) -> float:
        if self.sections_total == 0:
            return 0.0
        return self.sections_completed / self.sections_total

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter": self.chapter,
            "stage": self.stage.value,
            "sections_total": self.sections_total,
            "sections_completed": self.sections_completed,
            "completion_ratio": round(self.completion_ratio, 4),
        }


@dataclass(frozen=True)
class MilestoneSnapshot:
    """Point-in-time thesis progress summary."""

    milestones: tuple[Milestone, ...]
    overall_progress: float
    chapters_total: int
    chapters_complete: int
    computed_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.overall_progress <= 100.0:
            raise ValueError(
                "overall_progress must be between 0.0 and 100.0."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestones": [m.to_dict() for m in self.milestones],
            "overall_progress": round(self.overall_progress, 2),
            "chapters_total": self.chapters_total,
            "chapters_complete": self.chapters_complete,
            "computed_at": self.computed_at.isoformat(),
        }


# ── Report Model ──────────────────────────────────────────────


@dataclass(frozen=True)
class WorkflowReport:
    """Final structured output of a full workflow run.

    Produced by Stone 12. The Kernel decides what to do with it.
    """

    report_id: str
    pipeline: PipelineResult
    action_queue: ActionQueue
    milestones: MilestoneSnapshot
    lifecycles: tuple[ChapterLifecycle, ...]
    generated_at: datetime = field(default_factory=utc_now)

    @property
    def requires_attention(self) -> bool:
        """True if any critical or high-priority actions exist."""

        return (
            self.action_queue.critical_count > 0
            or self.action_queue.high_count > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "pipeline": self.pipeline.to_dict(),
            "action_queue": self.action_queue.to_dict(),
            "milestones": self.milestones.to_dict(),
            "lifecycles": [lc.to_dict() for lc in self.lifecycles],
            "generated_at": self.generated_at.isoformat(),
            "requires_attention": self.requires_attention,
        }
