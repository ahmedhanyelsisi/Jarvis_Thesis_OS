"""Academic command router with a narrow Kernel adapter boundary."""
from __future__ import annotations
import re
from ..research_planner.planner import ResearchPlanner
from ..citation_manager.citation_store import CitationStore
from ..literature_matrix.matrix import LiteratureMatrix
from ..thesis_manager.thesis_tracker import ThesisTracker


class AcademicWorkflowRouter:
    def __init__(self, kernel=None, planner=None, citations=None, literature=None, thesis=None):
        self.kernel = kernel
        self.planner = planner or ResearchPlanner()
        self.citations = citations or CitationStore()
        self.literature = literature or LiteratureMatrix()
        self.thesis = thesis or ThesisTracker()

    def route(self, command: str, **payload):
        if not isinstance(command, str):
            return {"command": "unrecognized", "request": ""}
        text = " ".join(command.split()).strip()
        if not text:
            return {"command": "unrecognized", "request": ""}
        lowered = text.lower()
        match = re.fullmatch(r"plan chapter\s+(\d+)(?:\s*[:\-]\s*(.*))?", lowered)
        if match:
            plan = self.planner.plan_chapter(int(match.group(1)), match.group(2))
            return {"command": "plan_chapter", "plan": plan}
        if lowered.startswith("plan chapter"):
            return {"command": "unrecognized", "request": text}
        if lowered == "add citation":
            if payload:
                record = self.citations.add(**payload)
                return {"command": "add_citation", "citation": record}
            return {"command": "add_citation", "message": "Provide citation fields to CitationStore.add()."}
        if lowered == "continue literature review":
            return {"command": "continue_literature_review", "entries": self.literature.entries()}
        if lowered == "show thesis progress":
            return {"command": "show_thesis_progress", "progress": self.thesis.progress()}
        # Unknown academic commands are handed back through the Kernel's public API.
        if self.kernel is not None and callable(getattr(self.kernel, "process_request", None)):
            return self.kernel.process_request(text)
        return {"command": "unrecognized", "request": text}

    process = route
    route_command = route


AcademicRouter = AcademicWorkflowRouter
