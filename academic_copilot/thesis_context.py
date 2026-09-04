"""Deterministic, read-only thesis context extraction for Stone 11."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


def _text(value: object, field: str, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    normalized = " ".join(value.split()).strip()
    if required and not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def _value(source: object, name: str, default=None):
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _items(value: object, field: str) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{field} must be an iterable, not a string")
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(f"{field} must be an iterable") from error


def _named_values(values: object, field: str) -> tuple[str, ...]:
    result: list[str] = []
    for item in _items(values, field):
        raw = _value(item, "value", item)
        text = _text(raw, field, required=True)
        if text not in result:
            result.append(text)
    return tuple(result)


@dataclass(frozen=True)
class ThesisContext:
    """A compact, stable snapshot used by all Stone 11 analyses.

    ``progress`` is a percentage in the inclusive range 0..100. Collections
    are tuples so a snapshot cannot be mutated after extraction.
    """

    title: str = ""
    chapters: tuple[str, ...] = ()
    sections: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    figures: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()
    progress: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _text(self.title, "title"))
        for name in ("chapters", "sections", "references", "figures", "tables"):
            values = _named_values(getattr(self, name), name)
            object.__setattr__(self, name, tuple(sorted(values, key=str.casefold)))
        if isinstance(self.progress, bool) or not isinstance(self.progress, (int, float)):
            raise TypeError("progress must be a number")
        progress = float(self.progress)
        if not isfinite(progress) or not 0.0 <= progress <= 100.0:
            raise ValueError("progress must be between 0 and 100")
        object.__setattr__(self, "progress", progress)

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "chapters": list(self.chapters),
            "sections": list(self.sections),
            "references": list(self.references),
            "figures": list(self.figures),
            "tables": list(self.tables),
            "progress": self.progress,
        }


class ThesisContextExtractor:
    """Convert Stone 10 snapshots and Stone 9 progress into a context model."""

    def extract(
        self,
        workspace: object | None = None,
        progress: object | None = None,
        *,
        title: str | None = None,
    ) -> ThesisContext:
        if workspace is None:
            source: object = {}
        elif callable(getattr(workspace, "discover", None)):
            source = workspace.discover()
        elif isinstance(workspace, Mapping) or hasattr(workspace, "documents"):
            source = workspace
        else:
            raise TypeError("workspace must be thesis workspace information or a Stone 10 workspace API")

        documents = _items(_value(source, "documents", ()), "documents")
        chapters: list[str] = list(_named_values(_value(source, "chapters", ()), "chapters"))
        sections: list[str] = list(_named_values(_value(source, "sections", ()), "sections"))
        references: list[str] = list(_named_values(_value(source, "references", ()), "references"))
        figures: list[str] = list(_named_values(_value(source, "figure_files", ()), "figures"))
        tables: list[str] = list(_named_values(_value(source, "tables", ()), "tables"))

        for document in documents:
            chapters.extend(_named_values(_value(document, "chapters", ()), "chapters"))
            sections.extend(_named_values(_value(document, "sections", ()), "sections"))
            references.extend(_named_values(_value(document, "citations", ()), "references"))
            for figure in _items(_value(document, "figures", ()), "figures"):
                identifier = (
                    _value(figure, "label")
                    or _value(figure, "path")
                    or _value(figure, "caption")
                )
                if identifier:
                    figures.append(_text(identifier, "figure", required=True))
            for environment in _items(_value(document, "environments", ()), "environments"):
                if str(_value(environment, "name", "")).casefold() == "table":
                    identifier = _value(environment, "label")
                    if identifier:
                        tables.append(_text(identifier, "table", required=True))

        raw_title = title if title is not None else _value(source, "title", "")
        raw_progress = progress if progress is not None else _value(source, "progress", 0.0)
        return ThesisContext(
            title=_text(raw_title, "title"),
            chapters=tuple(chapters),
            sections=tuple(sections),
            references=tuple(references),
            figures=tuple(figures),
            tables=tuple(tables),
            progress=self._progress_percentage(raw_progress),
        )

    @staticmethod
    def _progress_percentage(progress: object) -> float:
        if progress is None:
            return 0.0
        if isinstance(progress, bool):
            raise TypeError("progress must be numeric or thesis progress information")
        if isinstance(progress, (int, float)):
            return float(progress)

        chapters = _items(_value(progress, "chapters", ()), "progress chapters")
        if chapters:
            total_sections = sum(len(_items(_value(chapter, "sections", ()), "sections")) for chapter in chapters)
            completed_sections = sum(
                len(_items(_value(chapter, "completed_sections", ()), "completed sections"))
                for chapter in chapters
            )
            if total_sections:
                return round(completed_sections * 100.0 / total_sections, 2)
            completed = sum(str(_value(chapter, "completion_status", "")).casefold() == "completed" for chapter in chapters)
            return round(completed * 100.0 / len(chapters), 2)

        completed = _value(progress, "completed_chapters")
        total = _value(progress, "total_chapters")
        if completed is not None or total is not None:
            if isinstance(completed, bool) or not isinstance(completed, int):
                raise TypeError("completed_chapters must be an integer")
            if isinstance(total, bool) or not isinstance(total, int):
                raise TypeError("total_chapters must be an integer")
            if completed < 0 or total < 0 or completed > total:
                raise ValueError("chapter progress is invalid")
            return round(completed * 100.0 / total, 2) if total else 0.0

        if isinstance(progress, Mapping) and "percentage" in progress:
            return ThesisContextExtractor._progress_percentage(progress["percentage"])
        raise TypeError("progress must be numeric or thesis progress information")


def extract_thesis_context(
    workspace: object | None = None,
    progress: object | None = None,
    *,
    title: str | None = None,
) -> ThesisContext:
    """Functional facade for deterministic context extraction."""

    return ThesisContextExtractor().extract(workspace, progress, title=title)
