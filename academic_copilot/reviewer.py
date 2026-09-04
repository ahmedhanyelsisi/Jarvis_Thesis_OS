"""Deterministic supervisor/examiner-style chapter review."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


_CITATION = re.compile(r"\\(?:cite|citep|citet|textcite|parencite)\*?(?:\[[^\]]*\]){0,2}\{[^{}]+\}|\([A-Z][A-Za-z-]+(?: et al\.)?,? \d{4}[a-z]?\)")
_HEADING = re.compile(r"(?:^|\n)\s*(?:\\(?:chapter|section|subsection)\*?\{[^{}]+\}|#{1,4}\s+.+)")


def _text(value: object, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def _get(source: object, key: str, default: object = "") -> object:
    return source.get(key, default) if isinstance(source, Mapping) else getattr(source, key, default)


def _frozen_strings(values: object, field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"{field} must be an iterable of strings")
    try:
        result = {_text(value, field) for value in values}  # type: ignore[arg-type]
    except TypeError as error:
        if str(error).startswith(field):
            raise
        raise TypeError(f"{field} must be an iterable of strings") from error
    return tuple(sorted(result, key=str.casefold))


@dataclass(frozen=True)
class ReviewerRules:
    minimum_word_count: int = 100
    minimum_section_count: int = 2

    def __post_init__(self) -> None:
        for name in ("minimum_word_count", "minimum_section_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ReviewerReport:
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    improvement_suggestions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("strengths", "weaknesses", "missing_evidence", "improvement_suggestions"):
            object.__setattr__(self, name, _frozen_strings(getattr(self, name), name))

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "missing_evidence": list(self.missing_evidence),
            "improvement_suggestions": list(self.improvement_suggestions),
        }


class AcademicReviewer:
    """Apply a fixed rubric to chapter information; no model calls occur."""

    def __init__(self, rules: ReviewerRules | None = None) -> None:
        if rules is not None and not isinstance(rules, ReviewerRules):
            raise TypeError("rules must be ReviewerRules")
        self.rules = rules or ReviewerRules()

    def review(self, chapter: object) -> ReviewerReport:
        if isinstance(chapter, str):
            content = _text(chapter, "chapter")
            title = ""
            supplied_sections: tuple[object, ...] = ()
        elif isinstance(chapter, Mapping) or hasattr(chapter, "content"):
            content = _text(_get(chapter, "content"), "chapter content")
            title = _text(_get(chapter, "title"), "chapter title", required=False)
            sections = _get(chapter, "sections", ())
            if isinstance(sections, (str, bytes, bytearray)):
                raise TypeError("sections must be an iterable")
            try:
                supplied_sections = tuple(sections)  # type: ignore[arg-type]
            except TypeError as error:
                raise TypeError("sections must be an iterable") from error
        else:
            raise TypeError("chapter must be text or chapter information")

        words = re.findall(r"[A-Za-z][A-Za-z'-]*", content)
        citations = _CITATION.findall(content)
        headings = _HEADING.findall(content)
        section_count = max(len(headings), len(supplied_sections))
        lowered = content.casefold()
        evidence_signal = bool(re.search(r"\b(data|evidence|finding|result)s?\b", lowered))
        limitation_signal = bool(re.search(r"\b(limitations?|constraints?|threats? to validity)\b", lowered))
        claim_signal = bool(re.search(r"\b(argue|claim|demonstrate|indicate|show|suggest)\w*\b", lowered))

        strengths: list[str] = []
        weaknesses: list[str] = []
        missing: list[str] = []
        suggestions: list[str] = []
        if title:
            strengths.append("Chapter title is explicitly identified.")
        if section_count >= self.rules.minimum_section_count:
            strengths.append("Chapter has a visible multi-section structure.")
        else:
            weaknesses.append("Chapter structure is not sufficiently signposted.")
            suggestions.append("Add descriptive sections that follow the chapter argument.")
        if citations:
            strengths.append("Chapter includes traceable citation markers.")
        else:
            weaknesses.append("Chapter contains no citation markers.")
            missing.append("Source support for literature-dependent statements is absent.")
            suggestions.append("Attach relevant claims to entries already present in the bibliography.")
        if evidence_signal:
            strengths.append("Chapter explicitly signals evidence or findings.")
        elif claim_signal:
            missing.append("Explicit evidence for claim-bearing statements is not signposted.")
            suggestions.append("Pair each central claim with evidence and an interpretation step.")
        if limitation_signal:
            strengths.append("Chapter acknowledges limitations or validity boundaries.")
        else:
            weaknesses.append("Chapter does not state limitations or validity boundaries.")
            suggestions.append("Add a bounded limitations or validity subsection.")
        if len(words) < self.rules.minimum_word_count:
            weaknesses.append(f"Chapter is below the minimum review depth threshold of {self.rules.minimum_word_count} words.")
            suggestions.append("Develop the chapter before substantive examiner review.")
        return ReviewerReport(tuple(strengths), tuple(weaknesses), tuple(missing), tuple(suggestions))


def review_chapter(chapter: object) -> ReviewerReport:
    return AcademicReviewer().review(chapter)
