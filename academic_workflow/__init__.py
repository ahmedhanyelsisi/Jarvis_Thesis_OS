"""Stone 12 — Academic Workflow Orchestration Layer.

Public facade for the Kernel. Stone 12 owns workflow state representation
only. The Kernel owns all execution decisions.
"""

import threading

from .action_queue import ActionQueueBuilder
from .lifecycle import InvalidTransitionError, LifecycleManager
from .milestone_tracker import MilestoneTracker
from .models import (
    ActionCategory,
    ActionItem,
    ActionPriority,
    ActionQueue,
    ChapterLifecycle,
    Milestone,
    MilestoneSnapshot,
    PipelineResult,
    PipelineStep,
    PipelineStepStatus,
    StageTransition,
    ThesisStage,
    WorkflowReport,
)
from .report_builder import ReportBuilder
from .workflow import WorkflowSteps


class AcademicWorkflow:
    """Kernel-owned facade for the Stone 12 orchestration layer.

    Stone 12 owns workflow state representation only.
    The Kernel owns all execution decisions.
    """

    def __init__(self, copilot, workspace, router) -> None:
        self._copilot = copilot
        self._workspace = workspace
        self._router = router
        self._lifecycle = LifecycleManager()
        self._milestone_tracker = MilestoneTracker(self._lifecycle)
        self._action_builder = ActionQueueBuilder()
        self._workflow_steps = WorkflowSteps(copilot, workspace)
        self._last_report: WorkflowReport | None = None
        self._lock = threading.RLock()

    # ── Workflow ──────────────────────────────────────────────

    def run_workflow(
        self,
        *,
        chapter: str | None = None,
        chapter_texts: dict[str, str] | None = None,
        terminology: dict[str, tuple[str, ...]] | None = None,
        citation_keys: tuple[str, ...] | None = None,
        research_questions: tuple[str, ...] | None = None,
        title: str | None = None,
    ) -> WorkflowReport:
        """Collect analysis results and return a structured report.

        The Kernel calls this method. Stone 12 represents workflow state;
        the Kernel decides when and how to act on the report.
        """

        pipeline_result, raw = self._workflow_steps.run_steps(
            chapter=chapter,
            chapter_texts=chapter_texts,
            terminology=terminology,
            citation_keys=citation_keys,
            research_questions=research_questions,
            title=title,
        )

        action_queue = self._action_builder.build(
            thesis_structure=raw.get("thesis_structure"),
            citation_report=raw.get("citation_report"),
            consistency_report=raw.get("consistency_report"),
            reviewer_reports=raw.get("reviewer_reports"),
            gap_report=raw.get("gap_report"),
        )

        # Compute milestones from Stone 9 thesis progress.
        thesis_progress = None
        try:
            tracker = getattr(self._router, "thesis_tracker", None)
            if tracker is not None:
                thesis_progress = tracker.progress()
        except Exception:
            pass

        milestones = self._milestone_tracker.snapshot(thesis_progress)
        lifecycles = self._lifecycle.list_all()

        report = ReportBuilder.build(
            pipeline=pipeline_result,
            action_queue=action_queue,
            milestones=milestones,
            lifecycles=lifecycles,
        )

        with self._lock:
            self._last_report = report
            
        return report

    # ── Lifecycle ─────────────────────────────────────────────

    def get_lifecycle(self, chapter: str) -> ChapterLifecycle:
        """Return the current lifecycle state for a chapter."""

        return self._lifecycle.get(chapter)

    def advance_stage(
        self,
        chapter: str,
        target_stage: ThesisStage,
        reason: str = "",
    ) -> ChapterLifecycle:
        """Transition a chapter to a new lifecycle stage."""

        return self._lifecycle.advance(chapter, target_stage, reason)

    def list_lifecycles(self) -> tuple[ChapterLifecycle, ...]:
        """Return lifecycle states for all tracked chapters."""

        return self._lifecycle.list_all()

    # ── Milestones ────────────────────────────────────────────

    def get_milestones(self) -> MilestoneSnapshot:
        """Compute a point-in-time milestone snapshot."""

        thesis_progress = None
        try:
            tracker = getattr(self._router, "thesis_tracker", None)
            if tracker is not None:
                thesis_progress = tracker.progress()
        except Exception:
            pass

        return self._milestone_tracker.snapshot(thesis_progress)

    # ── Action Queue ──────────────────────────────────────────

    def get_actions(
        self,
        report: WorkflowReport | None = None,
    ) -> ActionQueue:
        """Return the action queue from the latest or a specific report."""

        with self._lock:
            target = report or self._last_report
            
        if target is None:
            return ActionQueue(items=())
        return target.action_queue


__all__ = [
    "AcademicWorkflow",
    "ActionCategory",
    "ActionItem",
    "ActionPriority",
    "ActionQueue",
    "ActionQueueBuilder",
    "ChapterLifecycle",
    "InvalidTransitionError",
    "LifecycleManager",
    "Milestone",
    "MilestoneSnapshot",
    "MilestoneTracker",
    "PipelineResult",
    "PipelineStep",
    "PipelineStepStatus",
    "ReportBuilder",
    "StageTransition",
    "ThesisStage",
    "WorkflowReport",
    "WorkflowSteps",
]
