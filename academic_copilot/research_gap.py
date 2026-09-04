"""Closed-world research-gap analysis over Stone 9 literature entries."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Mapping


_WORDS = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}")
_STOP_WORDS = frozenset(
    {
        "about", "after", "also", "among", "analysis", "based", "before",
        "being", "between", "could", "findings", "from", "have", "into",
        "limited", "method", "needs", "only", "other", "research", "results",
        "should", "study", "their", "there", "these", "this", "using", "with",
    }
)


def _get(item: object, name: str, default: object = "") -> object:
    return item.get(name, default) if isinstance(item, Mapping) else getattr(item, name, default)


def _clean(value: object, field: str, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    value = " ".join(value.split()).strip()
    if required and not value:
        raise ValueError(f"{field} must not be empty")
    return value


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        token.casefold()
        for token in _WORDS.findall(text)
        if token.casefold() not in _STOP_WORDS
    )


def _tuple(values: object, field: str) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"{field} must be an iterable, not a string")
    try:
        return tuple(values)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(f"{field} must be an iterable") from error


@dataclass(frozen=True)
class ResearchGapReport:
    dominant_themes: tuple[str, ...] = ()
    underrepresented_areas: tuple[str, ...] = ()
    missing_connections: tuple[str, ...] = ()
    possible_contribution_areas: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    gap_detection_mode: str = field(default="lexical", init=False)

    def __post_init__(self) -> None:
        for name in (
            "dominant_themes",
            "underrepresented_areas",
            "missing_connections",
            "possible_contribution_areas",
            "diagnostics",
        ):
            raw = _tuple(getattr(self, name), name)
            cleaned = tuple(sorted({_clean(value, name, required=True) for value in raw}, key=str.casefold))
            object.__setattr__(self, name, cleaned)
        if self.gap_detection_mode != "lexical":
            raise ValueError("gap_detection_mode is fixed to lexical")

    def to_dict(self) -> dict[str, object]:
        return {
            "dominant_themes": list(self.dominant_themes),
            "underrepresented_areas": list(self.underrepresented_areas),
            "missing_connections": list(self.missing_connections),
            "possible_contribution_areas": list(self.possible_contribution_areas),
            "diagnostics": list(self.diagnostics),
            "gap_detection_mode": self.gap_detection_mode,
        }


class ResearchGapAnalyzer:
    """Infer gaps only from supplied literature; it never retrieves sources."""

    def analyze(self, literature: object) -> ResearchGapReport:
        if literature is None:
            return ResearchGapReport(diagnostics=("missing_literature_input",))
        if callable(getattr(literature, "entries", None)):
            raw_entries = literature.entries()
        else:
            raw_entries = literature
        entries = _tuple(raw_entries, "literature")
        if not entries:
            return ResearchGapReport(diagnostics=("missing_literature_input",))
        
        token_sets: list[frozenset[str]] = []
        gap_tokens: Counter[str] = Counter()
        explicit_gaps: set[str] = set()
        diagnostics: list[str] = []
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, Mapping) and not hasattr(entry, "findings"):
                raise TypeError("literature entries must be mappings or Stone 9 literature records")
            title = _clean(_get(entry, "title"), "title")
            method = _clean(_get(entry, "method"), "method")
            findings = _clean(_get(entry, "findings"), "findings")
            limitations = _clean(_get(entry, "limitations"), "limitations")
            gap = _clean(_get(entry, "research_gap"), "research_gap")
            if not any((title, method, findings, limitations, gap)):
                diagnostics.append(f"incomplete_literature_entry:{index}")
            combined = _tokens(" ".join((title, method, findings, limitations, gap)))
            token_sets.append(combined)
            gap_area_tokens = _tokens(" ".join((limitations, gap)))
            gap_tokens.update(gap_area_tokens)
            if gap:
                explicit_gaps.add(gap)

        document_frequency = Counter(token for tokens in token_sets for token in tokens)
        repeated = [item for item in document_frequency.items() if item[1] >= 2]
        if repeated:
            dominant = tuple(token for token, _ in sorted(repeated, key=lambda item: (-item[1], item[0]))[:8])
        else:
            dominant = tuple(token for token, _ in sorted(document_frequency.items(), key=lambda item: (-item[1], item[0]))[:3])

        underrepresented = tuple(
            token
            for token, count in sorted(gap_tokens.items(), key=lambda item: (item[1], item[0]))
            if document_frequency[token] == 1
        )[:10]

        candidates = tuple(dict.fromkeys((*dominant[:5], *underrepresented[:5])))
        connections: list[str] = []
        for index, left in enumerate(candidates):
            for right in candidates[index + 1 :]:
                if not any(left in tokens and right in tokens for tokens in token_sets):
                    connections.append(f"{left} <-> {right}")

        contributions = tuple(f"Address documented gap: {gap}" for gap in sorted(explicit_gaps, key=str.casefold))
        if not contributions:
            contributions = tuple(f"Investigate underrepresented area: {area}" for area in underrepresented)
        return ResearchGapReport(
            dominant,
            underrepresented,
            tuple(connections[:10]),
            contributions,
            tuple(diagnostics),
        )


def analyze_research_gaps(literature: object) -> ResearchGapReport:
    return ResearchGapAnalyzer().analyze(literature)
