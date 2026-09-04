"""Controlled workflow state representation for the Stone 12 orchestration layer.

Stone 12 owns workflow state representation only.
The Kernel owns execution decisions — it decides when to call this module.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .models import PipelineResult, PipelineStep, PipelineStepStatus, utc_now


class WorkflowSteps:
    """Represent and collect analysis results from Stone 10/11 public APIs.

    Each step calls a Kernel-injected facade method. Steps are independent —
    a step failure is recorded as SKIPPED and collection continues.
    """

    def __init__(self, copilot: Any, workspace: Any) -> None:
        self._copilot = copilot
        self._workspace = workspace

    def run_steps(
        self,
        *,
        chapter: str | None = None,
        chapter_texts: dict[str, str] | None = None,
        terminology: dict[str, tuple[str, ...]] | None = None,
        citation_keys: tuple[str, ...] | None = None,
        research_questions: tuple[str, ...] | None = None,
        title: str | None = None,
    ) -> tuple[PipelineResult, dict[str, Any]]:
        """Collect results from all workflow steps.

        Returns the structured pipeline result plus raw data for
        the action queue builder.
        """

        started = utc_now()
        steps: list[PipelineStep] = []
        raw: dict[str, Any] = {}

        # Step 1: Workspace scan (Stone 10)
        step, data = self._step_workspace_scan()
        steps.append(step)
        raw["thesis_structure"] = data

        # Step 2: Citation check (Stone 10)
        step, data = self._step_citation_check(raw.get("thesis_structure"))
        steps.append(step)
        raw["citation_report"] = data

        # Step 3: Context extraction (Stone 11)
        step, data = self._step_context_extraction(title)
        steps.append(step)
        raw["thesis_context"] = data

        # Step 4: Research gap analysis (Stone 11)
        step, data = self._step_gap_analysis()
        steps.append(step)
        raw["gap_report"] = data

        # Step 5: Consistency check (Stone 11)
        step, data = self._step_consistency_check(
            chapter_texts, terminology, citation_keys, research_questions,
        )
        steps.append(step)
        raw["consistency_report"] = data

        # Step 6: Chapter review (Stone 11)
        step, data = self._step_chapter_review(chapter_texts)
        steps.append(step)
        raw["reviewer_reports"] = data

        pipeline_result = PipelineResult(
            pipeline_id=str(uuid4()),
            steps=tuple(steps),
            chapter=chapter,
            started_at=started,
            completed_at=utc_now(),
        )

        return pipeline_result, raw

    # ── Individual Steps ──────────────────────────────────────

    def _step_workspace_scan(self) -> tuple[PipelineStep, Any]:
        try:
            structure = self._workspace.discover()
            findings = (
                len(getattr(structure, "duplicate_labels", ()) or ())
                + len(getattr(structure, "unresolved_references", ()) or ())
            )
            return PipelineStep(
                name="workspace_scan",
                status=PipelineStepStatus.COMPLETED,
                findings_count=findings,
                source_stone=10,
                data=structure,
            ), structure
        except Exception as e:
            return PipelineStep(
                name="workspace_scan",
                status=PipelineStepStatus.SKIPPED,
                findings_count=0,
                source_stone=10,
                error_message=str(e),
            ), None

    def _step_citation_check(
        self,
        structure: Any,
    ) -> tuple[PipelineStep, Any]:
        try:
            report = self._workspace.check_citations(structure)
            findings = sum(
                len(getattr(report, attr, ()) or ())
                for attr in (
                    "missing_bibliography_entries",
                    "unused_bibliography_entries",
                    "duplicate_citation_keys",
                    "missing_bibliography_files",
                    "malformed_bibliography_entries",
                )
            )
            return PipelineStep(
                name="citation_check",
                status=PipelineStepStatus.COMPLETED,
                findings_count=findings,
                source_stone=10,
                data=report,
            ), report
        except Exception as e:
            return PipelineStep(
                name="citation_check",
                status=PipelineStepStatus.SKIPPED,
                findings_count=0,
                source_stone=10,
                error_message=str(e),
            ), None

    def _step_context_extraction(
        self,
        title: str | None,
    ) -> tuple[PipelineStep, Any]:
        try:
            context = self._copilot.thesis_context(title)
            return PipelineStep(
                name="context_extraction",
                status=PipelineStepStatus.COMPLETED,
                findings_count=0,
                source_stone=11,
                data=context,
            ), context
        except Exception as e:
            return PipelineStep(
                name="context_extraction",
                status=PipelineStepStatus.SKIPPED,
                findings_count=0,
                source_stone=11,
                error_message=str(e),
            ), None

    def _step_gap_analysis(self) -> tuple[PipelineStep, Any]:
        try:
            report = self._copilot.analyze_research_gaps()
            findings = sum(
                len(getattr(report, attr, ()) or ())
                for attr in (
                    "underrepresented_areas",
                    "missing_connections",
                    "possible_contribution_areas",
                )
            )
            return PipelineStep(
                name="research_gap_analysis",
                status=PipelineStepStatus.COMPLETED,
                findings_count=findings,
                source_stone=11,
                data=report,
            ), report
        except Exception as e:
            return PipelineStep(
                name="research_gap_analysis",
                status=PipelineStepStatus.SKIPPED,
                findings_count=0,
                source_stone=11,
                error_message=str(e),
            ), None

    def _step_consistency_check(
        self,
        chapter_texts: dict[str, str] | None,
        terminology: dict[str, tuple[str, ...]] | None,
        citation_keys: tuple[str, ...] | None,
        research_questions: tuple[str, ...] | None,
    ) -> tuple[PipelineStep, Any]:
        if not chapter_texts:
            return PipelineStep(
                name="consistency_check",
                status=PipelineStepStatus.NOT_APPLICABLE,
                findings_count=0,
                source_stone=11,
            ), None

        try:
            report = self._copilot.check_consistency(
                chapter_texts=chapter_texts,
                terminology=terminology or {},
                citation_keys=citation_keys or (),
                research_questions=research_questions or (),
            )
            findings = sum(
                len(getattr(report, attr, ()) or ())
                for attr in (
                    "terminology_consistency",
                    "citation_references",
                    "chapter_alignment",
                    "research_question_alignment",
                )
            )
            return PipelineStep(
                name="consistency_check",
                status=PipelineStepStatus.COMPLETED,
                findings_count=findings,
                source_stone=11,
                data=report,
            ), report
        except Exception as e:
            return PipelineStep(
                name="consistency_check",
                status=PipelineStepStatus.SKIPPED,
                findings_count=0,
                source_stone=11,
                error_message=str(e),
            ), None

    def _step_chapter_review(
        self,
        chapter_texts: dict[str, str] | None,
    ) -> tuple[PipelineStep, dict[str, Any] | None]:
        if not chapter_texts:
            return PipelineStep(
                name="chapter_review",
                status=PipelineStepStatus.NOT_APPLICABLE,
                findings_count=0,
                source_stone=11,
            ), None

        try:
            reports: dict[str, Any] = {}
            total_findings = 0
            for chapter_name, text in sorted(chapter_texts.items()):
                report = self._copilot.review_chapter(text)
                reports[chapter_name] = report
                for attr in (
                    "weaknesses",
                    "missing_evidence",
                    "improvement_suggestions",
                ):
                    total_findings += len(getattr(report, attr, ()) or ())
            return PipelineStep(
                name="chapter_review",
                status=PipelineStepStatus.COMPLETED,
                findings_count=total_findings,
                source_stone=11,
                data=reports,
            ), reports
        except Exception as e:
            return PipelineStep(
                name="chapter_review",
                status=PipelineStepStatus.SKIPPED,
                findings_count=0,
                source_stone=11,
                error_message=str(e),
            ), None
