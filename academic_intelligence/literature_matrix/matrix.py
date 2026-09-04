"""Structured literature-review matrix."""
from __future__ import annotations
from ..models import LiteratureEntry


class LiteratureMatrix:
    def __init__(self) -> None:
        self._entries: list[LiteratureEntry] = []

    def add_entry(self, entry: LiteratureEntry | None = None, **fields) -> LiteratureEntry:
        item = entry if entry is not None else LiteratureEntry(**fields)
        if not isinstance(item, LiteratureEntry):
            raise TypeError("entry must be a LiteratureEntry")
        self._entries.append(item)
        return item

    add = add_entry

    def entries(self) -> tuple[LiteratureEntry, ...]:
        return tuple(sorted(self._entries, key=lambda e: (e.year, e.author.casefold(), e.title.casefold())))

    list_entries = entries

    def search(self, term: str) -> tuple[LiteratureEntry, ...]:
        if not isinstance(term, str):
            raise TypeError("search term must be a string")
        needle = term.strip().casefold()
        if not needle:
            return ()
        return tuple(e for e in self._entries if needle in repr(e).lower())


LiteratureReviewMatrix = LiteratureMatrix
