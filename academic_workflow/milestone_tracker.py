"""Compute thesis milestone snapshots from Stone 9 progress and lifecycle state.

No persistence — computes a fresh snapshot on each call.
"""

from __future__ import annotations

from typing import Any

from .lifecycle import LifecycleManager
from .models import Milestone, MilestoneSnapshot, ThesisStage, utc_now


class MilestoneTracker:
    """Derive milestone snapshots by combining Stone 9 progress with lifecycle.

    Purely functional — no owned state, no persistence.
    """

    def __init__(self, lifecycle: LifecycleManager) -> None:
        self._lifecycle = lifecycle

    def snapshot(self, thesis_progress: Any = None) -> MilestoneSnapshot:
        """Compute a point-in-time milestone snapshot."""

        milestones: list[Milestone] = []

        # Derive milestones from Stone 9 ThesisProgress chapters.
        if thesis_progress is not None:
            for chapter in getattr(thesis_progress, "chapters", ()):
                chapter_num = str(getattr(chapter, "number", ""))
                chapter_title = getattr(chapter, "title", chapter_num)

                if chapter_title and chapter_title != chapter_num:
                    label = f"Chapter {chapter_num}: {chapter_title}"
                else:
                    label = f"Chapter {chapter_num}"

                sections = getattr(chapter, "sections", ())
                completed = getattr(chapter, "completed_sections", ())

                lifecycle = self._lifecycle.get(label)

                milestones.append(Milestone(
                    chapter=label,
                    stage=lifecycle.stage,
                    sections_total=len(sections),
                    sections_completed=len(completed),
                ))

        # Include chapters tracked in lifecycle but absent from Stone 9.
        tracked_labels = {m.chapter for m in milestones}
        for lc in self._lifecycle.list_all():
            if lc.chapter not in tracked_labels:
                milestones.append(Milestone(
                    chapter=lc.chapter,
                    stage=lc.stage,
                    sections_total=0,
                    sections_completed=0,
                ))

        milestones.sort()

        chapters_total = len(milestones)
        chapters_complete = sum(
            1 for m in milestones if m.stage == ThesisStage.COMPLETE
        )

        overall = self._compute_overall_progress(milestones)

        return MilestoneSnapshot(
            milestones=tuple(milestones),
            overall_progress=round(min(100.0, overall), 2),
            chapters_total=chapters_total,
            chapters_complete=chapters_complete,
            computed_at=utc_now(),
        )

    @staticmethod
    def _compute_overall_progress(milestones: list[Milestone]) -> float:
        """Deterministic progress: stage position weighted across chapters."""

        if not milestones:
            return 0.0

        stage_order = list(ThesisStage)
        max_index = len(stage_order) - 1

        total_weight = 0.0
        for milestone in milestones:
            stage_index = stage_order.index(milestone.stage)
            stage_progress = stage_index / max_index if max_index else 0.0
            section_progress = milestone.completion_ratio
            # Stage progress dominates; section progress adds detail.
            chapter_weight = (
                0.7 * stage_progress + 0.3 * section_progress
            ) * 100.0
            total_weight += chapter_weight

        return total_weight / len(milestones)
