from academic_intelligence import (
    AcademicWorkflowRouter, CitationRecord, CitationStore, LiteratureEntry,
    LiteratureMatrix, ResearchPlan, ResearchPlanner, ResearchTask, ThesisTracker,
)
import dataclasses
import pytest
from jarvis import Jarvis


def test_package_imports_and_planner_creation():
    planner = ResearchPlanner()
    plan = planner.plan_research("impact of reproducible science")
    assert plan.goal.startswith("impact")
    assert len(plan.steps) == 5
    assert planner.plan_chapter(2).chapters == ("Chapter 2",)


def test_citation_storage_bibtex_and_duplicate_detection():
    store = CitationStore()
    record = store.add(CitationRecord("smith2024", "A Study", "Smith, J.", 2024, "Journal"))
    assert store.get("smith2024") == record
    assert "@article{smith2024" in store.generate_bibtex("smith2024")
    assert store.duplicate(CitationRecord("other", "A Study", "Smith, J.", 2024))


def test_literature_matrix_and_thesis_tracking():
    matrix = LiteratureMatrix()
    matrix.add_entry(LiteratureEntry("Doe", 2023, "case study", "supports X", "small sample", "needs scale"))
    assert len(matrix.entries()) == 1
    tracker = ThesisTracker()
    tracker.add_chapter(2, "Literature Review", ["2.1", "2.2"], citation_requirements=3)
    tracker.mark_section_complete(2, "2.1")
    tracker.add_citation(2)
    progress = tracker.get_progress()
    assert progress.total_chapters == 1 and progress.chapters[0].citations_added == 1


def test_workflow_routing_and_kernel_compatibility():
    router = AcademicWorkflowRouter()
    assert router.route("plan chapter 2")["command"] == "plan_chapter"
    assert router.route("continue literature review")["command"] == "continue_literature_review"
    assert router.route("show thesis progress")["command"] == "show_thesis_progress"


def test_models_are_immutable_and_validate_invalid_state():
    assert dataclasses.is_dataclass(ResearchTask) and ResearchTask.__dataclass_params__.frozen
    with pytest.raises(ValueError):
        ResearchTask("")
    with pytest.raises(TypeError):
        ResearchPlan("goal", ("not a task",))
    with pytest.raises(ValueError):
        CitationStore().add(CitationRecord("bad key!", "Title", "Author", 2024))


def test_defensive_empty_and_missing_states():
    assert LiteratureMatrix().entries() == ()
    assert LiteratureMatrix().search("") == ()
    tracker = ThesisTracker()
    assert tracker.update_section(99, "missing") is None
    assert tracker.add_citation(99) is None
    with pytest.raises(ValueError):
        tracker.add_chapter(1, "Intro", ["1.1"], citation_requirements=-1)


def test_citation_types_and_kernel_fallback_are_safe():
    store = CitationStore()
    store.add(CitationRecord("book2024", "Book", "Author", 2024, citation_type="book"))
    assert store.to_bibtex("book2024").startswith("@book{")
    class Kernel:
        def process_request(self, request):
            return {"kernel_request": request}
    router = AcademicWorkflowRouter(kernel=Kernel())
    assert router.route("unrecognized academic request") == {"kernel_request": "unrecognized academic request"}
    assert router.route("plan chapter X")["command"] == "unrecognized"


def test_kernel_wake_word_normalization():
    router = AcademicWorkflowRouter()
    cases = {
        "Jarvis plan chapter 2": "plan_chapter",
        "jarvis add citation": "add_citation",
        "  JARVIS   continue   literature review  ": "continue_literature_review",
        "Jarvis show thesis progress": "show_thesis_progress",
        "plan chapter 2": "plan_chapter",
    }
    for request, intent in cases.items():
        cleaned = Jarvis.normalize_request(request)
        assert router.route(cleaned)["command"] == intent
    assert Jarvis.normalize_request("   Jarvis   ") == ""
