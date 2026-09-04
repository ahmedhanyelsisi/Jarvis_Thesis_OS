"""Stone 9: Academic Research Intelligence Layer (ARIL)."""
from .models import CitationRecord, LiteratureEntry, ResearchPlan, ResearchTask, ThesisChapter, ThesisProgress
from .research_planner.planner import ResearchPlanner, Planner
from .citation_manager.citation_store import CitationStore, CitationManager
from .literature_matrix.matrix import LiteratureMatrix, LiteratureReviewMatrix
from .thesis_manager.thesis_tracker import ThesisTracker, ThesisManager
from .workflows.academic_router import AcademicWorkflowRouter, AcademicRouter

__all__ = ["CitationRecord", "LiteratureEntry", "ResearchPlan", "ResearchTask", "ThesisChapter", "ThesisProgress", "ResearchPlanner", "Planner", "CitationStore", "CitationManager", "LiteratureMatrix", "LiteratureReviewMatrix", "ThesisTracker", "ThesisManager", "AcademicWorkflowRouter", "AcademicRouter"]
