"""Deterministic thesis structure and progress tracking."""
from __future__ import annotations
from dataclasses import replace
from ..models import ThesisChapter, ThesisProgress


class ThesisTracker:
    def __init__(self) -> None:
        self._chapters: dict[int, ThesisChapter] = {}

    def add_chapter(self, number: int, title: str, sections=(), citation_requirements: int = 0) -> ThesisChapter:
        if isinstance(sections, str):
            raise TypeError("sections must be an iterable of section names")
        if not isinstance(citation_requirements, int) or isinstance(citation_requirements, bool) or citation_requirements < 0:
            raise ValueError("citation_requirements must be a non-negative integer")
        chapter = ThesisChapter(number, title, tuple(sections), (), citation_requirements, 0)
        self._chapters[number] = chapter
        return chapter

    track_chapter = add_chapter

    def update_section(self, chapter: int, section: str, completed: bool = True) -> ThesisChapter | None:
        current = self._chapters.get(chapter)
        if current is None:
            return None
        if section not in current.sections:
            raise ValueError(f"Unknown section for chapter {chapter}: {section}")
        if not isinstance(completed, bool):
            raise TypeError("completed must be a boolean")
        done = list(current.completed_sections)
        if completed and section not in done: done.append(section)
        if not completed and section in done: done.remove(section)
        updated = replace(current, completed_sections=tuple(done))
        self._chapters[chapter] = updated
        return updated

    mark_section_complete = update_section

    def add_citation(self, chapter: int, count: int = 1) -> ThesisChapter | None:
        current = self._chapters.get(chapter)
        if current is None:
            return None
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("count must be a non-negative integer")
        updated = replace(current, citations_added=max(0, current.citations_added + count))
        self._chapters[chapter] = updated
        return updated

    def progress(self) -> ThesisProgress:
        return ThesisProgress(tuple(self._chapters[n] for n in sorted(self._chapters)))

    get_progress = progress


ThesisManager = ThesisTracker
