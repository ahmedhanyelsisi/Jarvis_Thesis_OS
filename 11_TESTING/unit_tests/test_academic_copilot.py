"""Stone 11 deterministic Academic Copilot tests."""

import ast
from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path

import pytest

from academic_copilot import (
    AcademicCopilot,
    AcademicReviewer,
    ConsistencyChecker,
    EnvironmentCompatibilityChecker,
    ResearchGapAnalyzer,
    ReviewerRules,
    ThesisContext,
    analyze_paragraph,
    audit_dependencies,
    detect_repetition,
    extract_thesis_context,
    identify_missing_argument,
    review_chapter,
    suggest_structure,
)
from academic_intelligence import LiteratureEntry
from jarvis import Jarvis
from thesis_workspace import DocumentElement, FigureElement, LatexDocument, SourceLocation, ThesisStructure


def _snapshot(tmp_path):
    document = LatexDocument(
        "main.tex",
        chapters=(DocumentElement("Introduction", SourceLocation("main.tex", 2)),),
        sections=(DocumentElement("Motivation", SourceLocation("main.tex", 4)),),
        citations=(DocumentElement("smith2024", SourceLocation("main.tex", 8)),),
        figures=(FigureElement("figures/model.png", "Model", "fig:model", SourceLocation("main.tex", 10)),),
    )
    return ThesisStructure(tmp_path, ("main.tex",), ("references.bib",), ("figures/model.png",), (document,))


def test_context_extraction_is_complete_ordered_and_serializable(tmp_path):
    context = extract_thesis_context(
        _snapshot(tmp_path),
        {"chapters": ({"sections": ("A", "B"), "completed_sections": ("A",)},)},
        title="Controlled Thesis",
    )

    assert context.title == "Controlled Thesis"
    assert context.chapters == ("Introduction",)
    assert context.sections == ("Motivation",)
    assert context.references == ("smith2024",)
    assert context.figures == ("fig:model", "figures/model.png")
    assert context.tables == ()
    assert context.progress == 50.0
    json.dumps(context.to_dict(), sort_keys=True)


def test_empty_and_missing_thesis_information_is_stable():
    assert extract_thesis_context() == ThesisContext()
    assert extract_thesis_context({"title": None, "chapters": None}) == ThesisContext()


def test_research_gap_detection_uses_only_supplied_matrix():
    entries = (
        LiteratureEntry("A", 2022, "survey", "automation improves review", "urban sample", "rural validation"),
        LiteratureEntry("B", 2023, "survey", "automation supports review", "short duration", "longitudinal validation"),
    )
    report = ResearchGapAnalyzer().analyze(entries)

    assert "automation" in report.dominant_themes
    assert "rural" in report.underrepresented_areas
    assert report.possible_contribution_areas == (
        "Address documented gap: longitudinal validation",
        "Address documented gap: rural validation",
    )
    assert report == ResearchGapAnalyzer().analyze(entries)
    assert report.gap_detection_mode == "lexical"
    assert report.to_dict()["gap_detection_mode"] == "lexical"


def test_missing_literature_data_returns_declared_lexical_empty_report():
    assert ResearchGapAnalyzer().analyze(None) == ResearchGapAnalyzer().analyze(())
    report = ResearchGapAnalyzer().analyze(({},))
    assert report.dominant_themes == ()
    assert report.gap_detection_mode == "lexical"


def test_writing_analysis_returns_bounded_structured_recommendations():
    paragraph = "This study shows change because the data supports the claim. However, the study may be limited."
    analysis = analyze_paragraph(paragraph)
    argument = identify_missing_argument(paragraph)
    repetition = detect_repetition("model model model evidence")
    structure = suggest_structure("discussion", ("interpretation", "limitations"))

    assert analysis.word_count > 0
    assert "claim" in argument.present_components
    assert repetition.repeated_terms[0].term == "model"
    assert "comparison with literature" in structure.missing_components
    assert all(hasattr(item, "code") for item in analysis.recommendations)


def test_consistency_check_covers_all_four_dimensions():
    context = ThesisContext(
        chapters=("Introduction",),
        sections=("Scope",),
        references=("known", "missing"),
    )
    report = ConsistencyChecker().check(
        context,
        {"Introduction": "The ML method answers the first aim.", "Appendix": "Unaligned material."},
        terminology={"machine learning": ("ML",)},
        citation_keys=("known",),
        research_questions=("How does climate adaptation improve resilience?",),
    )

    assert report.terminology_consistency[0].code == "nonpreferred_term"
    assert report.citation_references[0].code == "missing_citation_record"
    assert report.chapter_alignment[0].code == "undeclared_chapter"
    assert report.research_question_alignment[0].code == "research_question_unaddressed"
    assert not report.is_consistent


def test_incomplete_research_question_is_diagnosed_safely():
    report = ConsistencyChecker().check(
        ThesisContext(chapters=("Introduction",)),
        {"Introduction": "Background material."},
        research_questions=("Why?",),
    )
    assert [issue.code for issue in report.research_question_alignment] == [
        "research_question_incomplete"
    ]


def test_reviewer_output_is_deterministic_and_rule_bound():
    report = review_chapter(
        {
            "title": "Results",
            "sections": ("Overview", "Findings"),
            "content": "The results show an effect, but the chapter offers no supporting source.",
        }
    )

    assert "Chapter title is explicitly identified." in report.strengths
    assert report.missing_evidence
    assert report.weaknesses
    assert report == review_chapter({"title": "Results", "sections": ("Overview", "Findings"), "content": "The results show an effect, but the chapter offers no supporting source."})


def test_malformed_reviewer_rules_are_rejected():
    with pytest.raises(ValueError, match="positive"):
        ReviewerRules(minimum_word_count=0)
    with pytest.raises(TypeError, match="ReviewerRules"):
        AcademicReviewer(rules={"minimum_word_count": 10})


def test_all_models_are_immutable_and_defensively_copy_inputs():
    supplied = ["Second", "First"]
    context = ThesisContext(chapters=supplied)
    supplied.clear()

    assert is_dataclass(ThesisContext) and ThesisContext.__dataclass_params__.frozen
    assert context.chapters == ("First", "Second")
    with pytest.raises(FrozenInstanceError):
        context.title = "Changed"


@pytest.mark.parametrize(
    "operation",
    (
        lambda: extract_thesis_context(object()),
        lambda: ThesisContext(progress=101),
        lambda: ResearchGapAnalyzer().analyze("not entries"),
        lambda: analyze_paragraph(123),
        lambda: detect_repetition("valid text", threshold=1),
        lambda: suggest_structure("unknown"),
        lambda: ConsistencyChecker().check("not context"),
        lambda: review_chapter({"content": ""}),
    ),
)
def test_invalid_inputs_are_rejected(operation):
    with pytest.raises((TypeError, ValueError)):
        operation()


def test_kernel_exposes_additive_academic_copilot_adapter(tmp_path):
    jarvis = Jarvis(
        config={
            "memory": {"enabled": False, "database_path": str(tmp_path / "memory.sqlite")},
            "knowledge": {"enabled": False},
            "voice": {"enabled": False},
            "thesis_workspace": {"root": str(tmp_path)},
        }
    )
    try:
        assert isinstance(jarvis.academic_copilot, AcademicCopilot)
        assert jarvis.academic_copilot.thesis_context() == ThesisContext()
        assert jarvis.academic_copilot.analyze_research_gaps().dominant_themes == ()
        assert callable(jarvis.process_request)
        assert callable(jarvis.process_workflow)
    finally:
        jarvis.close()


def test_dependency_audit_absence_is_safe_and_does_not_break_startup(tmp_path):
    def failed_lookup(_name):
        raise RuntimeError("simulated unavailable tooling")

    report = audit_dependencies(module_finder=failed_lookup)
    assert report.status == "unavailable"
    assert "failed safely" in report.reason
    assert report.package_changes_performed is False

    jarvis = Jarvis(
        config={
            "memory": {"enabled": False, "database_path": str(tmp_path / "memory.sqlite")},
            "knowledge": {"enabled": False},
            "voice": {"enabled": False},
            "thesis_workspace": {"root": str(tmp_path)},
        }
    )
    try:
        assert isinstance(jarvis.academic_copilot, AcademicCopilot)
    finally:
        jarvis.close()


def test_dependency_audit_missing_tool_has_deterministic_diagnostic():
    first = audit_dependencies(module_finder=lambda _name: None)
    second = audit_dependencies(module_finder=lambda _name: None)

    assert first == second
    assert first.status == "unavailable"
    assert "not installed" in first.reason
    assert "no package changes performed" in first.reason


def test_dependency_audit_detects_available_tool_without_executing_it():
    report = audit_dependencies(module_finder=lambda _name: object())
    assert report.status == "available"
    assert "offline advisory source" in report.reason
    assert report.package_changes_performed is False


def test_environment_compatibility_no_drift():
    report = EnvironmentCompatibilityChecker().check(
        ("Alpha_Package==1.2.3", "beta==2.0.0"),
        installed_packages={"alpha-package": "1.2.3", "BETA": "2.0.0"},
    )
    assert report.status == "compatible"
    assert report.missing_packages == ()
    assert report.version_conflicts == ()


def test_environment_compatibility_reports_missing_package():
    report = EnvironmentCompatibilityChecker().check(
        ("present==1.0.0", "missing==2.0.0"),
        installed_packages={"present": "1.0.0"},
    )
    assert report.status == "drift_detected"
    assert report.missing_packages == ("missing",)


def test_environment_compatibility_classifies_version_drift():
    report = EnvironmentCompatibilityChecker().check(
        ("zeta==1.4.2", "alpha==2.0.0", "middle==3.2.1"),
        installed_packages={"zeta": "1.4.3", "alpha": "3.0.0", "middle": "3.1.9"},
    )

    assert report.status == "drift_detected"
    assert [item.package for item in report.version_conflicts] == ["alpha", "middle", "zeta"]
    assert [item.package for item in report.newer_patch_versions] == ["zeta"]
    assert [item.package for item in report.incompatible_major_versions] == ["alpha"]


def test_environment_compatibility_empty_requirements_is_safe():
    report = EnvironmentCompatibilityChecker().check("", installed_packages={})
    assert report.status == "compatible"
    assert report.missing_packages == ()
    assert report.version_conflicts == ()
    assert report.warnings == ("No exact package pins were available for comparison.",)


def test_invalid_recommendation_requests_are_rejected():
    with pytest.raises(ValueError):
        suggest_structure(" ")
    with pytest.raises(TypeError):
        suggest_structure("introduction", "context")
    with pytest.raises(ValueError):
        analyze_paragraph(" ")


def test_stone_11_output_ordering_is_deterministic():
    context = ThesisContext(chapters=("zeta", "Alpha", "beta", "Alpha"))
    report = EnvironmentCompatibilityChecker().check(
        ("zeta==1.0.0", "alpha==1.0.0"),
        installed_packages={},
    )
    assert context.chapters == ("Alpha", "beta", "zeta")
    assert report.missing_packages == ("alpha", "zeta")


def test_stone_11_static_architecture_boundaries():
    root = Path(__file__).resolve().parents[2]
    package = root / "academic_copilot"
    banned = {
        "agents", "agent_manager", "jarvis_agents", "reasoning", "memory",
        "cognitive_ui", "voice", "socket", "requests", "urllib", "httpx",
        "aiohttp", "subprocess",
    }
    imported_roots: set[str] = set()
    for source_path in sorted(package.glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_roots.add(node.module.split(".")[0])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"exec", "eval", "compile", "__import__"}

    assert imported_roots.isdisjoint(banned)
    assert imported_roots.isdisjoint({"academic_intelligence", "thesis_workspace", "jarvis"})
    kernel_source = (root / "01_CORE_KERNEL" / "jarvis.py").read_text(encoding="utf-8")
    assert "from academic_copilot import AcademicCopilot" in kernel_source
    assert "self.academic_copilot = AcademicCopilot(" in kernel_source
