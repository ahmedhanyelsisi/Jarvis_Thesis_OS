"""Validated in-memory citation store (no external database or network access)."""
from __future__ import annotations

import re
from ..models import CitationRecord


class CitationStore:
    _ENTRY_TYPES = {"article": "article", "book": "book", "conference": "inproceedings", "thesis": "phdthesis", "misc": "misc"}
    _KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")

    def __init__(self) -> None:
        self._records: dict[str, CitationRecord] = {}

    def add(self, citation: CitationRecord | None = None, **fields) -> CitationRecord:
        try:
            record = citation if citation is not None else CitationRecord(**fields)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid citation: {exc}") from exc
        if not isinstance(record, CitationRecord):
            raise TypeError("citation must be a CitationRecord")
        if not self._KEY.fullmatch(record.key):
            raise ValueError("citation key must start with a letter and contain only letters, digits, _, ., :, or -")
        if self.is_duplicate(record):
            raise ValueError(f"Duplicate citation: {record.key}")
        self._records[record.key] = record
        return record

    add_citation = add

    def get(self, key: str) -> CitationRecord | None:
        return self._records.get(key)

    get_citation = get

    def all(self) -> tuple[CitationRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    list_citations = all

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.casefold())

    def is_duplicate(self, citation: CitationRecord) -> bool:
        if not isinstance(citation, CitationRecord):
            raise TypeError("citation must be a CitationRecord")
        fingerprint = (self._norm(citation.title), self._norm(citation.author), citation.year)
        return any(item.key == citation.key or
                   (fingerprint == (self._norm(item.title), self._norm(item.author), item.year)) or
                   (citation.doi and self._norm(item.doi) == self._norm(citation.doi))
                   for item in self._records.values())

    duplicate = is_duplicate

    def to_bibtex(self, key: str) -> str:
        record = self._records.get(key)
        if record is None:
            raise KeyError(f"Unknown citation key: {key}")

        def esc(value: str) -> str:
            return value.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("{", r"\{").replace("}", r"\}")

        fields = [f"  author = {{{esc(record.author)}}}", f"  title = {{{esc(record.title)}}}", f"  year = {{{record.year}}}"]
        if record.venue:
            fields.append(f"  journal = {{{esc(record.venue)}}}")
        if record.doi:
            fields.append(f"  doi = {{{esc(record.doi)}}}")
        if record.url:
            fields.append(f"  url = {{{esc(record.url)}}}")
        return "@" + self._ENTRY_TYPES[record.citation_type] + "{" + record.key + ",\n" + ",\n".join(fields) + "\n}"

    generate_bibtex = to_bibtex


CitationManager = CitationStore
