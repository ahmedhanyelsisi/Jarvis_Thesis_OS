"""Assemble structured WorkflowReport from workflow results."""

from __future__ import annotations

from uuid import uuid4

from .models import (
    ActionQueue,
    ChapterLifecycle,
    MilestoneSnapshot,
    PipelineResult,
    WorkflowReport,
    utc_now,
)


class ReportBuilder:
    """Assemble a WorkflowReport from components produced by the workflow.

    Pure assembly — no logic, no transformation, no persistence.
    """

    @staticmethod
    def build(
        pipeline: PipelineResult,
        action_queue: ActionQueue,
        milestones: MilestoneSnapshot,
        lifecycles: tuple[ChapterLifecycle, ...],
    ) -> WorkflowReport:
        """Assemble a complete, immutable workflow report."""

        return WorkflowReport(
            report_id=str(uuid4()),
            pipeline=pipeline,
            action_queue=action_queue,
            milestones=milestones,
            lifecycles=lifecycles,
            generated_at=utc_now(),
        )
