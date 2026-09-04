"""Deterministic conversion of Stone 9–11 findings into prioritized actions.

All priority assignments are fixed mappings from finding type to severity level.
No AI scoring. No heuristics. No thresholds.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .models import (
    ActionCategory,
    ActionItem,
    ActionPriority,
    ActionQueue,
    PRIORITY_RANK,
    utc_now,
)


def _action_id(category: str, description: str) -> str:
    """Compute a deterministic 8-hex-char ID from category and description."""

    digest = hashlib.sha256(
        f"{category}:{description}".encode("utf-8")
    ).hexdigest()
    return digest[:8]


class ActionQueueBuilder:
    """Convert Stone 10/11 report objects into a sorted, deduplicated ActionQueue.

    Every finding type maps to exactly one priority level. The mapping is
    defined by the static methods below and cannot be overridden at runtime.
    """

    def build(
        self,
        *,
        thesis_structure: Any = None,
        citation_report: Any = None,
        consistency_report: Any = None,
        reviewer_reports: dict[str, Any] | None = None,
        gap_report: Any = None,
    ) -> ActionQueue:
        """Build a complete action queue from available Stone 10/11 reports."""

        items: list[ActionItem] = []

        if thesis_structure is not None:
            items.extend(self._from_thesis_structure(thesis_structure))

        if citation_report is not None:
            items.extend(self._from_citation_report(citation_report))

        if consistency_report is not None:
            items.extend(self._from_consistency_report(consistency_report))

        if reviewer_reports:
            for chapter, report in sorted(reviewer_reports.items()):
                items.extend(self._from_reviewer_report(report, chapter))

        if gap_report is not None:
            items.extend(self._from_gap_report(gap_report))

        deduplicated = self._deduplicate(items)

        sorted_items = sorted(
            deduplicated,
            key=lambda item: (
                PRIORITY_RANK[item.priority],
                item.category.value,
                item.action_id,
            ),
        )

        return ActionQueue(
            items=tuple(sorted_items),
            generated_at=utc_now(),
        )

    # ── Stone 10: ThesisStructure ─────────────────────────────

    @staticmethod
    def _from_thesis_structure(structure: Any) -> list[ActionItem]:
        actions: list[ActionItem] = []

        for label in getattr(structure, "duplicate_labels", ()) or ():
            desc = f"Resolve duplicate label: {label}"
            actions.append(ActionItem(
                priority=ActionPriority.CRITICAL,
                category=ActionCategory.STRUCTURE,
                action_id=_action_id("structure", desc),
                description=desc,
                source_stone=10,
            ))

        for ref in getattr(structure, "unresolved_references", ()) or ():
            desc = f"Fix unresolved reference: {ref}"
            actions.append(ActionItem(
                priority=ActionPriority.HIGH,
                category=ActionCategory.STRUCTURE,
                action_id=_action_id("structure", desc),
                description=desc,
                source_stone=10,
            ))

        return actions

    # ── Stone 10: CitationReport ──────────────────────────────

    @staticmethod
    def _from_citation_report(report: Any) -> list[ActionItem]:
        actions: list[ActionItem] = []

        for bib_file in getattr(report, "missing_bibliography_files", ()) or ():
            desc = f"Add missing bibliography file: {bib_file}"
            actions.append(ActionItem(
                priority=ActionPriority.CRITICAL,
                category=ActionCategory.CITATION,
                action_id=_action_id("citation", desc),
                description=desc,
                source_stone=10,
            ))

        for entry in getattr(report, "missing_bibliography_entries", ()) or ():
            key = getattr(entry, "key", str(entry))
            desc = f"Add bibliography entry for cited key: {key}"
            actions.append(ActionItem(
                priority=ActionPriority.HIGH,
                category=ActionCategory.CITATION,
                action_id=_action_id("citation", desc),
                description=desc,
                source_stone=10,
            ))

        for dup in getattr(report, "duplicate_citation_keys", ()) or ():
            key = getattr(dup, "key", str(dup))
            desc = f"Resolve duplicate citation key: {key}"
            actions.append(ActionItem(
                priority=ActionPriority.HIGH,
                category=ActionCategory.CITATION,
                action_id=_action_id("citation", desc),
                description=desc,
                source_stone=10,
            ))

        for entry in getattr(report, "malformed_bibliography_entries", ()) or ():
            key = getattr(entry, "key", str(entry))
            desc = f"Fix malformed bibliography entry: {key}"
            actions.append(ActionItem(
                priority=ActionPriority.MEDIUM,
                category=ActionCategory.CITATION,
                action_id=_action_id("citation", desc),
                description=desc,
                source_stone=10,
            ))

        for entry in getattr(report, "unused_bibliography_entries", ()) or ():
            key = getattr(entry, "key", str(entry))
            desc = f"Remove unused bibliography entry or add citation: {key}"
            actions.append(ActionItem(
                priority=ActionPriority.LOW,
                category=ActionCategory.CITATION,
                action_id=_action_id("citation", desc),
                description=desc,
                source_stone=10,
            ))

        return actions

    # ── Stone 11: ConsistencyReport ───────────────────────────

    @staticmethod
    def _from_consistency_report(report: Any) -> list[ActionItem]:
        actions: list[ActionItem] = []

        for issue in getattr(report, "terminology_consistency", ()) or ():
            msg = getattr(issue, "message", str(issue))
            desc = f"Standardize terminology: {msg}"
            actions.append(ActionItem(
                priority=ActionPriority.HIGH,
                category=ActionCategory.CONSISTENCY,
                action_id=_action_id("consistency", desc),
                description=desc,
                source_stone=11,
            ))

        for issue in getattr(report, "citation_references", ()) or ():
            msg = getattr(issue, "message", str(issue))
            desc = f"Fix citation reference: {msg}"
            actions.append(ActionItem(
                priority=ActionPriority.HIGH,
                category=ActionCategory.CONSISTENCY,
                action_id=_action_id("consistency", desc),
                description=desc,
                source_stone=11,
            ))

        for issue in getattr(report, "chapter_alignment", ()) or ():
            msg = getattr(issue, "message", str(issue))
            desc = f"Align chapter structure: {msg}"
            actions.append(ActionItem(
                priority=ActionPriority.MEDIUM,
                category=ActionCategory.CONSISTENCY,
                action_id=_action_id("consistency", desc),
                description=desc,
                source_stone=11,
            ))

        for issue in getattr(report, "research_question_alignment", ()) or ():
            msg = getattr(issue, "message", str(issue))
            desc = f"Strengthen research question coverage: {msg}"
            actions.append(ActionItem(
                priority=ActionPriority.MEDIUM,
                category=ActionCategory.CONSISTENCY,
                action_id=_action_id("consistency", desc),
                description=desc,
                source_stone=11,
            ))

        return actions

    # ── Stone 11: ReviewerReport ──────────────────────────────

    @staticmethod
    def _from_reviewer_report(report: Any, chapter: str) -> list[ActionItem]:
        actions: list[ActionItem] = []

        for evidence in getattr(report, "missing_evidence", ()) or ():
            desc = f"Add evidence: {evidence}"
            actions.append(ActionItem(
                priority=ActionPriority.HIGH,
                category=ActionCategory.REVIEW,
                action_id=_action_id("review", f"{chapter}:{desc}"),
                description=desc,
                source_stone=11,
                chapter=chapter,
            ))

        for weakness in getattr(report, "weaknesses", ()) or ():
            desc = f"Address weakness: {weakness}"
            actions.append(ActionItem(
                priority=ActionPriority.MEDIUM,
                category=ActionCategory.REVIEW,
                action_id=_action_id("review", f"{chapter}:{desc}"),
                description=desc,
                source_stone=11,
                chapter=chapter,
            ))

        for suggestion in getattr(report, "improvement_suggestions", ()) or ():
            desc = f"Consider improvement: {suggestion}"
            actions.append(ActionItem(
                priority=ActionPriority.LOW,
                category=ActionCategory.REVIEW,
                action_id=_action_id("review", f"{chapter}:{desc}"),
                description=desc,
                source_stone=11,
                chapter=chapter,
            ))

        return actions

    # ── Stone 11: ResearchGapReport ───────────────────────────

    @staticmethod
    def _from_gap_report(report: Any) -> list[ActionItem]:
        actions: list[ActionItem] = []

        for area in getattr(report, "underrepresented_areas", ()) or ():
            desc = f"Expand coverage of underrepresented area: {area}"
            actions.append(ActionItem(
                priority=ActionPriority.MEDIUM,
                category=ActionCategory.RESEARCH_GAP,
                action_id=_action_id("research_gap", desc),
                description=desc,
                source_stone=11,
            ))

        for conn in getattr(report, "missing_connections", ()) or ():
            desc = f"Add missing connection: {conn}"
            actions.append(ActionItem(
                priority=ActionPriority.MEDIUM,
                category=ActionCategory.RESEARCH_GAP,
                action_id=_action_id("research_gap", desc),
                description=desc,
                source_stone=11,
            ))

        for area in getattr(report, "possible_contribution_areas", ()) or ():
            desc = f"Develop contribution area: {area}"
            actions.append(ActionItem(
                priority=ActionPriority.LOW,
                category=ActionCategory.RESEARCH_GAP,
                action_id=_action_id("research_gap", desc),
                description=desc,
                source_stone=11,
            ))

        return actions

    # ── Deduplication ─────────────────────────────────────────

    @staticmethod
    def _deduplicate(items: list[ActionItem]) -> list[ActionItem]:
        """Remove duplicate actions by action_id, keeping first occurrence."""

        seen: dict[str, ActionItem] = {}
        for item in items:
            if item.action_id not in seen:
                seen[item.action_id] = item
        return list(seen.values())
