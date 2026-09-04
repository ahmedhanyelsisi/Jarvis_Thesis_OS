"""Stone 12 — Academic Workflow Orchestration Layer tests.

Focused test suite: immutable models, lifecycle transitions, invalid
transitions, deterministic action ordering, Kernel-only integration,
and report generation.
"""

import ast
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from academic_workflow import (
    AcademicWorkflow,
    ActionCategory,
    ActionItem,
    ActionPriority,
    ActionQueue,
    ActionQueueBuilder,
    ChapterLifecycle,
    InvalidTransitionError,
    LifecycleManager,
    Milestone,
    MilestoneSnapshot,
    PipelineResult,
    PipelineStep,
    PipelineStepStatus,
    ReportBuilder,
    StageTransition,
    ThesisStage,
    WorkflowReport,
    WorkflowSteps,
)


# ── Helpers ───────────────────────────────────────────────────


def _make_milestone_snapshot(**overrides):
    defaults = dict(
        milestones=(),
        overall_progress=0.0,
        chapters_total=0,
        chapters_complete=0,
    )
    defaults.update(overrides)
    return MilestoneSnapshot(**defaults)


def _make_pipeline_result(**overrides):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    defaults = dict(
        pipeline_id="test-id",
        steps=(),
        chapter=None,
        started_at=now,
        completed_at=now,
    )
    defaults.update(overrides)
    return PipelineResult(**defaults)


def _make_action_queue(*items):
    return ActionQueue(items=tuple(items))


def _make_report(**overrides):
    defaults = dict(
        report_id="rpt-001",
        pipeline=_make_pipeline_result(),
        action_queue=ActionQueue(items=()),
        milestones=_make_milestone_snapshot(),
        lifecycles=(),
    )
    defaults.update(overrides)
    return WorkflowReport(**defaults)


# ══════════════════════════════════════════════════════════════
# 1. MODEL IMMUTABILITY
# ══════════════════════════════════════════════════════════════


class TestModelImmutability:
    """All Stone 12 models must be frozen dataclasses."""

    def test_chapter_lifecycle_is_frozen(self):
        lc = ChapterLifecycle(chapter="Ch1", stage=ThesisStage.PLANNING)
        with pytest.raises(FrozenInstanceError):
            lc.stage = ThesisStage.DRAFTING  # type: ignore[misc]

    def test_action_item_is_frozen(self):
        item = ActionItem(
            priority=ActionPriority.HIGH,
            category=ActionCategory.CITATION,
            action_id="abc12345",
            description="test",
            source_stone=10,
        )
        with pytest.raises(FrozenInstanceError):
            item.priority = ActionPriority.LOW  # type: ignore[misc]

    def test_workflow_report_is_frozen(self):
        report = _make_report()
        with pytest.raises(FrozenInstanceError):
            report.report_id = "changed"  # type: ignore[misc]

    def test_milestone_snapshot_is_frozen(self):
        snap = _make_milestone_snapshot()
        with pytest.raises(FrozenInstanceError):
            snap.overall_progress = 99.9  # type: ignore[misc]

    def test_milestone_is_frozen(self):
        m = Milestone(
            chapter="Ch1", stage=ThesisStage.PLANNING,
            sections_total=5, sections_completed=2,
        )
        with pytest.raises(FrozenInstanceError):
            m.sections_completed = 3  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════
# 2. MODEL VALIDATION
# ══════════════════════════════════════════════════════════════


class TestModelValidation:
    """Models reject invalid construction arguments."""

    def test_action_item_rejects_invalid_source_stone(self):
        with pytest.raises(ValueError, match="source_stone"):
            ActionItem(
                priority=ActionPriority.HIGH,
                category=ActionCategory.CITATION,
                action_id="x",
                description="d",
                source_stone=99,
            )

    def test_milestone_snapshot_rejects_progress_over_100(self):
        with pytest.raises(ValueError, match="overall_progress"):
            MilestoneSnapshot(
                milestones=(), overall_progress=101.0,
                chapters_total=0, chapters_complete=0,
            )

    def test_milestone_rejects_completed_exceeding_total(self):
        with pytest.raises(ValueError, match="sections_completed"):
            Milestone(
                chapter="Ch1", stage=ThesisStage.PLANNING,
                sections_total=3, sections_completed=5,
            )

    def test_chapter_lifecycle_rejects_empty_chapter(self):
        with pytest.raises(ValueError, match="non-empty"):
            ChapterLifecycle(chapter="   ", stage=ThesisStage.PLANNING)


# ══════════════════════════════════════════════════════════════
# 3. MODEL SERIALIZATION
# ══════════════════════════════════════════════════════════════


class TestModelSerialization:
    """Every to_dict() must produce JSON-serializable output."""

    def test_action_item_serializable(self):
        item = ActionItem(
            priority=ActionPriority.CRITICAL,
            category=ActionCategory.STRUCTURE,
            action_id="abc",
            description="test",
            source_stone=10,
        )
        data = item.to_dict()
        assert json.dumps(data)
        assert data["priority"] == "critical"

    def test_workflow_report_serializable(self):
        report = _make_report()
        data = report.to_dict()
        serialized = json.dumps(data)
        assert serialized
        assert "report_id" in data

    def test_chapter_lifecycle_serializable(self):
        lc = ChapterLifecycle(chapter="Ch1", stage=ThesisStage.ANALYSIS)
        data = lc.to_dict()
        assert json.dumps(data)
        assert data["stage"] == "analysis"


# ══════════════════════════════════════════════════════════════
# 4. LIFECYCLE VALID TRANSITIONS
# ══════════════════════════════════════════════════════════════


class TestLifecycleValidTransitions:
    """Valid transitions must succeed and record history."""

    def test_planning_to_drafting(self):
        mgr = LifecycleManager()
        result = mgr.advance("Ch1", ThesisStage.DRAFTING)
        assert result.stage == ThesisStage.DRAFTING

    def test_drafting_to_analysis(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        result = mgr.advance("Ch1", ThesisStage.ANALYSIS)
        assert result.stage == ThesisStage.ANALYSIS

    def test_analysis_to_revision(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        mgr.advance("Ch1", ThesisStage.ANALYSIS)
        result = mgr.advance("Ch1", ThesisStage.REVISION, reason="issues found")
        assert result.stage == ThesisStage.REVISION
        assert result.history[-1].reason == "issues found"

    def test_analysis_to_review(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        mgr.advance("Ch1", ThesisStage.ANALYSIS)
        result = mgr.advance("Ch1", ThesisStage.REVIEW)
        assert result.stage == ThesisStage.REVIEW

    def test_full_lifecycle_path(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        mgr.advance("Ch1", ThesisStage.ANALYSIS)
        mgr.advance("Ch1", ThesisStage.REVIEW)
        mgr.advance("Ch1", ThesisStage.FINALIZATION)
        result = mgr.advance("Ch1", ThesisStage.COMPLETE)
        assert result.stage == ThesisStage.COMPLETE
        assert len(result.history) == 5

    def test_revision_cycle(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        mgr.advance("Ch1", ThesisStage.ANALYSIS)
        mgr.advance("Ch1", ThesisStage.REVISION)
        result = mgr.advance("Ch1", ThesisStage.ANALYSIS)
        assert result.stage == ThesisStage.ANALYSIS
        assert len(result.history) == 4

    def test_new_chapter_defaults_to_planning(self):
        mgr = LifecycleManager()
        lc = mgr.get("NewChapter")
        assert lc.stage == ThesisStage.PLANNING
        assert lc.history == ()


# ══════════════════════════════════════════════════════════════
# 5. LIFECYCLE INVALID TRANSITIONS
# ══════════════════════════════════════════════════════════════


class TestLifecycleInvalidTransitions:
    """Invalid transitions must raise InvalidTransitionError."""

    def test_planning_to_analysis_rejected(self):
        mgr = LifecycleManager()
        with pytest.raises(InvalidTransitionError, match="planning.*analysis"):
            mgr.advance("Ch1", ThesisStage.ANALYSIS)

    def test_complete_to_anything_rejected(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        mgr.advance("Ch1", ThesisStage.ANALYSIS)
        mgr.advance("Ch1", ThesisStage.REVIEW)
        mgr.advance("Ch1", ThesisStage.FINALIZATION)
        mgr.advance("Ch1", ThesisStage.COMPLETE)
        with pytest.raises(InvalidTransitionError):
            mgr.advance("Ch1", ThesisStage.PLANNING)

    def test_drafting_to_review_rejected(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        with pytest.raises(InvalidTransitionError):
            mgr.advance("Ch1", ThesisStage.REVIEW)

    def test_revision_to_complete_rejected(self):
        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        mgr.advance("Ch1", ThesisStage.ANALYSIS)
        mgr.advance("Ch1", ThesisStage.REVISION)
        with pytest.raises(InvalidTransitionError):
            mgr.advance("Ch1", ThesisStage.COMPLETE)


# ══════════════════════════════════════════════════════════════
# 6. DETERMINISTIC ACTION ORDERING
# ══════════════════════════════════════════════════════════════


class TestDeterministicActionOrdering:
    """Action queues must be sorted by priority rank, then category, then ID."""

    def test_critical_before_high(self):
        builder = ActionQueueBuilder()
        structure = SimpleNamespace(
            duplicate_labels=("fig:dup",),
            unresolved_references=("ref:missing",),
        )
        queue = builder.build(thesis_structure=structure)
        assert queue.items[0].priority == ActionPriority.CRITICAL
        assert queue.items[1].priority == ActionPriority.HIGH

    def test_high_before_medium_before_low(self):
        builder = ActionQueueBuilder()
        report = SimpleNamespace(
            missing_bibliography_entries=(SimpleNamespace(key="k1"),),
            unused_bibliography_entries=(SimpleNamespace(key="k2"),),
            duplicate_citation_keys=(),
            missing_bibliography_files=(),
            malformed_bibliography_entries=(SimpleNamespace(key="k3"),),
        )
        queue = builder.build(citation_report=report)
        priorities = [item.priority for item in queue.items]
        assert priorities == [
            ActionPriority.HIGH,
            ActionPriority.MEDIUM,
            ActionPriority.LOW,
        ]

    def test_duplicate_actions_are_deduplicated(self):
        builder = ActionQueueBuilder()
        structure = SimpleNamespace(
            duplicate_labels=("fig:x", "fig:x"),
            unresolved_references=(),
        )
        queue = builder.build(thesis_structure=structure)
        assert queue.total == 1

    def test_action_id_is_deterministic(self):
        builder = ActionQueueBuilder()
        s1 = SimpleNamespace(duplicate_labels=("fig:a",), unresolved_references=())
        s2 = SimpleNamespace(duplicate_labels=("fig:a",), unresolved_references=())
        q1 = builder.build(thesis_structure=s1)
        q2 = builder.build(thesis_structure=s2)
        assert q1.items[0].action_id == q2.items[0].action_id


# ══════════════════════════════════════════════════════════════
# 7. ACTION PRIORITY MAPPING
# ══════════════════════════════════════════════════════════════


class TestActionPriorityMapping:
    """Each finding type maps to exactly one deterministic priority level."""

    def test_missing_bib_file_is_critical(self):
        builder = ActionQueueBuilder()
        report = SimpleNamespace(
            missing_bibliography_files=("refs.bib",),
            missing_bibliography_entries=(),
            unused_bibliography_entries=(),
            duplicate_citation_keys=(),
            malformed_bibliography_entries=(),
        )
        queue = builder.build(citation_report=report)
        assert queue.items[0].priority == ActionPriority.CRITICAL

    def test_missing_bibliography_entry_is_high(self):
        builder = ActionQueueBuilder()
        report = SimpleNamespace(
            missing_bibliography_files=(),
            missing_bibliography_entries=(SimpleNamespace(key="smith2024"),),
            unused_bibliography_entries=(),
            duplicate_citation_keys=(),
            malformed_bibliography_entries=(),
        )
        queue = builder.build(citation_report=report)
        assert queue.items[0].priority == ActionPriority.HIGH

    def test_underrepresented_area_is_medium(self):
        builder = ActionQueueBuilder()
        gap = SimpleNamespace(
            underrepresented_areas=("deep learning",),
            missing_connections=(),
            possible_contribution_areas=(),
        )
        queue = builder.build(gap_report=gap)
        assert queue.items[0].priority == ActionPriority.MEDIUM

    def test_unused_bibliography_is_low(self):
        builder = ActionQueueBuilder()
        report = SimpleNamespace(
            missing_bibliography_files=(),
            missing_bibliography_entries=(),
            unused_bibliography_entries=(SimpleNamespace(key="old2020"),),
            duplicate_citation_keys=(),
            malformed_bibliography_entries=(),
        )
        queue = builder.build(citation_report=report)
        assert queue.items[0].priority == ActionPriority.LOW


# ══════════════════════════════════════════════════════════════
# 8. REPORT GENERATION
# ══════════════════════════════════════════════════════════════


class TestReportGeneration:
    """WorkflowReport assembly and properties."""

    def test_report_assembled_with_all_components(self):
        pipeline = _make_pipeline_result()
        actions = ActionQueue(items=())
        milestones = _make_milestone_snapshot()
        lifecycles = (
            ChapterLifecycle(chapter="Ch1", stage=ThesisStage.PLANNING),
        )
        report = ReportBuilder.build(pipeline, actions, milestones, lifecycles)
        assert report.report_id
        assert report.pipeline is pipeline
        assert report.action_queue is actions
        assert report.milestones is milestones
        assert report.lifecycles == lifecycles

    def test_requires_attention_true_with_critical(self):
        critical = ActionItem(
            priority=ActionPriority.CRITICAL,
            category=ActionCategory.STRUCTURE,
            action_id="x", description="d", source_stone=10,
        )
        report = _make_report(action_queue=_make_action_queue(critical))
        assert report.requires_attention is True

    def test_requires_attention_false_with_low_only(self):
        low = ActionItem(
            priority=ActionPriority.LOW,
            category=ActionCategory.CITATION,
            action_id="y", description="d", source_stone=10,
        )
        report = _make_report(action_queue=_make_action_queue(low))
        assert report.requires_attention is False


# ══════════════════════════════════════════════════════════════
# 9. MILESTONE COMPUTATION
# ══════════════════════════════════════════════════════════════


class TestMilestoneComputation:
    """Milestone snapshots derived from progress and lifecycle."""

    def test_empty_thesis_zero_progress(self):
        from academic_workflow.milestone_tracker import MilestoneTracker

        mgr = LifecycleManager()
        tracker = MilestoneTracker(mgr)
        snap = tracker.snapshot()
        assert snap.overall_progress == 0.0
        assert snap.chapters_total == 0

    def test_milestone_includes_lifecycle_chapters(self):
        from academic_workflow.milestone_tracker import MilestoneTracker

        mgr = LifecycleManager()
        mgr.advance("Ch1", ThesisStage.DRAFTING)
        tracker = MilestoneTracker(mgr)
        snap = tracker.snapshot()
        assert snap.chapters_total == 1
        assert snap.milestones[0].chapter == "Ch1"
        assert snap.milestones[0].stage == ThesisStage.DRAFTING


# ══════════════════════════════════════════════════════════════
# 10. KERNEL INTEGRATION
# ══════════════════════════════════════════════════════════════


class TestKernelIntegration:
    """Stone 12 integrates correctly with the Kernel."""

    def test_jarvis_has_academic_workflow_attribute(self):
        from jarvis import Jarvis

        config = {
            "memory": {"enabled": False},
            "knowledge": {"enabled": False},
            "voice": {"enabled": False},
        }
        jarvis = Jarvis(config=config)
        try:
            assert hasattr(jarvis, "academic_workflow")
            assert isinstance(jarvis.academic_workflow, AcademicWorkflow)
        finally:
            jarvis.close()

    def test_facade_accepts_stone_9_10_11_facades(self):
        copilot = SimpleNamespace()
        workspace = SimpleNamespace()
        router = SimpleNamespace()
        aw = AcademicWorkflow(copilot, workspace, router)
        assert aw is not None

    def test_get_actions_returns_empty_before_workflow(self):
        copilot = SimpleNamespace()
        workspace = SimpleNamespace()
        router = SimpleNamespace()
        aw = AcademicWorkflow(copilot, workspace, router)
        queue = aw.get_actions()
        assert queue.total == 0


# ══════════════════════════════════════════════════════════════
# 11. ARCHITECTURE BOUNDARY ENFORCEMENT
# ══════════════════════════════════════════════════════════════


class TestArchitectureBoundary:
    """Stone 12 must not import forbidden modules."""

    def test_no_forbidden_imports_in_academic_workflow(self):
        """Verify academic_workflow/ contains zero forbidden imports."""

        package_dir = Path(__file__).resolve().parents[2] / "academic_workflow"
        assert package_dir.is_dir(), f"Package not found: {package_dir}"

        forbidden_modules = {
            "socket", "requests", "urllib", "httpx",
            "subprocess", "sqlite3",
        }
        forbidden_names = {"exec", "eval", "open"}
        forbidden_from = {
            "memory", "reasoning", "voice", "cognitive_ui",
            "knowledge_system",
        }

        violations: list[str] = []

        for source_file in sorted(package_dir.glob("*.py")):
            tree = ast.parse(source_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in forbidden_modules:
                            violations.append(
                                f"{source_file.name}: import {alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        root = node.module.split(".")[0]
                        if root in forbidden_modules | forbidden_from:
                            violations.append(
                                f"{source_file.name}: from {node.module}"
                            )
                elif isinstance(node, ast.Name):
                    if node.id in forbidden_names:
                        if isinstance(node.ctx, ast.Load):
                            # Allow hashlib usage, only flag bare exec/eval/open
                            violations.append(
                                f"{source_file.name}: bare name {node.id!r}"
                            )

        assert not violations, (
            "Forbidden imports or names found in academic_workflow/:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ══════════════════════════════════════════════════════════════
# 12. HARDENING PHASE VALIDATION
# ══════════════════════════════════════════════════════════════


class TestHardeningValidations:
    """Tests covering newly added defensive validations."""

    def test_action_item_rejects_bad_priority_type(self):
        with pytest.raises(TypeError, match="priority must be an ActionPriority"):
            ActionItem(
                priority="critical",  # type: ignore
                category=ActionCategory.CITATION,
                action_id="x",
                description="d",
                source_stone=10,
            )

    def test_pipeline_step_captures_error_message(self):
        class FailingWorkspace:
            def discover(self):
                raise RuntimeError("Disk failed")
        
        steps = WorkflowSteps(SimpleNamespace(), FailingWorkspace())
        res, _ = steps.run_steps()
        scan_step = next(s for s in res.steps if s.name == "workspace_scan")
        assert scan_step.status == PipelineStepStatus.SKIPPED
        assert scan_step.error_message == "Disk failed"

    def test_academic_workflow_facade_locking(self):
        aw = AcademicWorkflow(SimpleNamespace(), SimpleNamespace(), SimpleNamespace())
        aw.get_actions()
        aw._last_report = _make_report()
        q = aw.get_actions()
        assert q.total == 0
