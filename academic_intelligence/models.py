"""Immutable, validated models shared by the Academic Research Intelligence Layer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


def _text(value: object, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    value = " ".join(value.split()).strip()
    if required and not value:
        raise ValueError(f"{field} must not be empty")
    return value


@dataclass(frozen=True)
class ResearchTask:
    title: str
    description: str = ""
    priority: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "description", _text(self.description, "description", required=False))
        if not isinstance(self.priority, int) or isinstance(self.priority, bool) or self.priority < 1:
            raise ValueError("priority must be a positive integer")

    def to_dict(self) -> dict:
        return {"title": self.title, "description": self.description, "priority": self.priority}


@dataclass(frozen=True)
class ResearchPlan:
    goal: str
    steps: Tuple[ResearchTask, ...]
    chapters: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "goal", _text(self.goal, "goal"))
        steps = tuple(self.steps)
        if not all(isinstance(step, ResearchTask) for step in steps):
            raise TypeError("steps must contain ResearchTask values")
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "chapters", tuple(_text(ch, "chapter") for ch in self.chapters))

    def to_dict(self) -> dict:
        return {"goal": self.goal, "steps": [step.to_dict() for step in self.steps], "chapters": list(self.chapters)}


@dataclass(frozen=True)
class CitationRecord:
    key: str
    title: str
    author: str
    year: int
    venue: str = ""
    doi: str = ""
    url: str = ""
    citation_type: str = "article"

    def __post_init__(self) -> None:
        for field in ("key", "title", "author"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        if not isinstance(self.year, int) or isinstance(self.year, bool) or not 1 <= self.year <= 9999:
            raise ValueError("year must be an integer between 1 and 9999")
        if self.citation_type not in {"article", "book", "conference", "thesis", "misc"}:
            raise ValueError("unsupported citation_type")
        for field in ("venue", "doi", "url"):
            object.__setattr__(self, field, _text(getattr(self, field), field, required=False))

    def to_dict(self) -> dict:
        return {field: getattr(self, field) for field in ("key", "title", "author", "year", "venue", "doi", "url", "citation_type")}


@dataclass(frozen=True)
class LiteratureEntry:
    author: str
    year: int
    method: str
    findings: str
    limitations: str
    research_gap: str
    title: str = ""

    def __post_init__(self) -> None:
        for field in ("author", "method", "findings", "limitations", "research_gap"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "title", _text(self.title, "title", required=False))
        if not isinstance(self.year, int) or isinstance(self.year, bool) or not 1 <= self.year <= 9999:
            raise ValueError("year must be an integer between 1 and 9999")

    def to_dict(self) -> dict:
        return {field: getattr(self, field) for field in ("author", "year", "method", "findings", "limitations", "research_gap", "title")}


@dataclass(frozen=True)
class ThesisChapter:
    number: int
    title: str
    sections: Tuple[str, ...] = ()
    completed_sections: Tuple[str, ...] = ()
    citation_requirements: int = 0
    citations_added: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.number, int) or isinstance(self.number, bool) or self.number < 1:
            raise ValueError("chapter number must be positive")
        object.__setattr__(self, "title", _text(self.title, "title"))
        sections = tuple(_text(s, "section") for s in self.sections)
        completed = tuple(_text(s, "completed section") for s in self.completed_sections)
        if not set(completed).issubset(set(sections)):
            raise ValueError("completed_sections must be declared in sections")
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "completed_sections", completed)
        for field in ("citation_requirements", "citations_added"):
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")

    @property
    def completion_status(self) -> str:
        return "completed" if self.sections and len(self.completed_sections) == len(self.sections) else "in_progress"

    def to_dict(self) -> dict:
        return {"number": self.number, "title": self.title, "sections": list(self.sections), "completed_sections": list(self.completed_sections), "citation_requirements": self.citation_requirements, "citations_added": self.citations_added, "completion_status": self.completion_status}


@dataclass(frozen=True)
class ThesisProgress:
    chapters: Tuple[ThesisChapter, ...] = ()

    def __post_init__(self) -> None:
        chapters = tuple(self.chapters)
        if not all(isinstance(chapter, ThesisChapter) for chapter in chapters):
            raise TypeError("chapters must contain ThesisChapter values")
        object.__setattr__(self, "chapters", chapters)

    @property
    def completed_chapters(self) -> int:
        return sum(ch.completion_status == "completed" for ch in self.chapters)

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)

    def to_dict(self) -> dict:
        return {"chapters": [
            c.to_dict()
            for c in self.chapters
        ], "completed_chapters": self.completed_chapters, "total_chapters": self.total_chapters}
