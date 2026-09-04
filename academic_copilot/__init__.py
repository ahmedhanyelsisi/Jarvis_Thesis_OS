"""Stone 11: deterministic Academic Copilot Layer."""

from __future__ import annotations

from typing import Mapping

from .consistency_checker import ConsistencyChecker, ConsistencyIssue, ConsistencyReport, check_consistency
from .environment_security import (
    DependencyAuditReport,
    DependencyVulnerability,
    EnvironmentCompatibilityChecker,
    EnvironmentFingerprint,
    EnvironmentReport,
    InstalledPackage,
    VersionDiagnostic,
    audit_dependencies,
    check_environment,
    environment_fingerprint,
)
from .research_gap import ResearchGapAnalyzer, ResearchGapReport, analyze_research_gaps
from .reviewer import AcademicReviewer, ReviewerReport, ReviewerRules, review_chapter
from .thesis_context import ThesisContext, ThesisContextExtractor, extract_thesis_context
from .writing_assistant import (
    ArgumentAssessment,
    ParagraphAnalysis,
    RepetitionFinding,
    RepetitionReport,
    StructureSuggestion,
    WritingRecommendation,
    analyze_paragraph,
    detect_repetition,
    identify_missing_argument,
    suggest_structure,
)


class AcademicCopilot:
    """Kernel-owned adapter over the public Stone 9 and Stone 10 APIs."""

    def __init__(self, academic_intelligence: object, thesis_workspace: object) -> None:
        if not hasattr(academic_intelligence, "literature") or not hasattr(academic_intelligence, "thesis"):
            raise TypeError("academic_intelligence must expose Stone 9 literature and thesis APIs")
        if not callable(getattr(thesis_workspace, "discover", None)):
            raise TypeError("thesis_workspace must expose the Stone 10 discover API")
        self._academic = academic_intelligence
        self._workspace = thesis_workspace
        self._contexts = ThesisContextExtractor()
        self._gaps = ResearchGapAnalyzer()
        self._consistency = ConsistencyChecker()
        self._reviewer = AcademicReviewer()

    def thesis_context(self, *, title: str | None = None) -> ThesisContext:
        return self._contexts.extract(
            self._workspace,
            self._academic.thesis.progress(),
            title=title,
        )

    context = thesis_context

    def analyze_research_gaps(self) -> ResearchGapReport:
        return self._gaps.analyze(self._academic.literature)

    research_gaps = analyze_research_gaps

    @staticmethod
    def analyze_paragraph(paragraph: str) -> ParagraphAnalysis:
        return analyze_paragraph(paragraph)

    @staticmethod
    def suggest_structure(section_type: str, existing_components: object = ()) -> StructureSuggestion:
        return suggest_structure(section_type, existing_components)

    @staticmethod
    def detect_repetition(text: str, *, threshold: int = 3) -> RepetitionReport:
        return detect_repetition(text, threshold=threshold)

    @staticmethod
    def identify_missing_argument(paragraph: str) -> ArgumentAssessment:
        return identify_missing_argument(paragraph)

    def check_consistency(
        self,
        chapter_texts: Mapping[str, str] | None = None,
        *,
        title: str | None = None,
        terminology: Mapping[str, object] | None = None,
        research_questions: object = (),
    ) -> ConsistencyReport:
        citation_keys = tuple(record.key for record in self._academic.citations.all())
        return self._consistency.check(
            self.thesis_context(title=title),
            chapter_texts,
            terminology=terminology,
            citation_keys=citation_keys,
            research_questions=research_questions,
        )

    def review_chapter(self, chapter: object) -> ReviewerReport:
        return self._reviewer.review(chapter)

    review = review_chapter


__all__ = [
    "AcademicCopilot",
    "AcademicReviewer",
    "ArgumentAssessment",
    "ConsistencyChecker",
    "ConsistencyIssue",
    "ConsistencyReport",
    "DependencyAuditReport",
    "DependencyVulnerability",
    "EnvironmentCompatibilityChecker",
    "EnvironmentFingerprint",
    "EnvironmentReport",
    "InstalledPackage",
    "ParagraphAnalysis",
    "RepetitionFinding",
    "RepetitionReport",
    "ResearchGapAnalyzer",
    "ResearchGapReport",
    "ReviewerReport",
    "ReviewerRules",
    "StructureSuggestion",
    "ThesisContext",
    "ThesisContextExtractor",
    "WritingRecommendation",
    "VersionDiagnostic",
    "analyze_paragraph",
    "analyze_research_gaps",
    "audit_dependencies",
    "check_consistency",
    "check_environment",
    "detect_repetition",
    "extract_thesis_context",
    "environment_fingerprint",
    "identify_missing_argument",
    "review_chapter",
    "suggest_structure",
]
