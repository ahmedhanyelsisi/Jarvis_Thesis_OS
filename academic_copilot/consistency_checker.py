"""Deterministic cross-thesis consistency checks."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from .thesis_context import ThesisContext


_LATEX_CITATION = re.compile(
    r"\\(?:cite|citep|citet|textcite|parencite)\*?(?:\[[^\]]*\]){0,2}\{(?P<keys>[^{}]+)\}"
)


def _text(value: object, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    normalized = " ".join(value.split()).strip()
    if required and not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def _strings(values: object, field: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"{field} must be an iterable of strings")
    try:
        return tuple(_text(value, field) for value in values)  # type: ignore[arg-type]
    except TypeError as error:
        if str(error).startswith(field):
            raise
        raise TypeError(f"{field} must be an iterable of strings") from error


@dataclass(frozen=True, order=True)
class ConsistencyIssue:
    code: str
    message: str
    locations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "code"))
        object.__setattr__(self, "message", _text(self.message, "message"))
        object.__setattr__(self, "locations", tuple(sorted(set(_strings(self.locations, "locations")), key=str.casefold)))

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "locations": list(self.locations)}


@dataclass(frozen=True)
class ConsistencyReport:
    terminology_consistency: tuple[ConsistencyIssue, ...] = ()
    citation_references: tuple[ConsistencyIssue, ...] = ()
    chapter_alignment: tuple[ConsistencyIssue, ...] = ()
    research_question_alignment: tuple[ConsistencyIssue, ...] = ()

    def __post_init__(self) -> None:
        for name in ("terminology_consistency", "citation_references", "chapter_alignment", "research_question_alignment"):
            issues = tuple(getattr(self, name))
            if not all(isinstance(issue, ConsistencyIssue) for issue in issues):
                raise TypeError(f"{name} must contain ConsistencyIssue values")
            object.__setattr__(self, name, tuple(sorted(issues)))

    @property
    def is_consistent(self) -> bool:
        return not any((self.terminology_consistency, self.citation_references, self.chapter_alignment, self.research_question_alignment))

    def to_dict(self) -> dict[str, object]:
        return {
            "terminology_consistency": [item.to_dict() for item in self.terminology_consistency],
            "citation_references": [item.to_dict() for item in self.citation_references],
            "chapter_alignment": [item.to_dict() for item in self.chapter_alignment],
            "research_question_alignment": [item.to_dict() for item in self.research_question_alignment],
            "is_consistent": self.is_consistent,
        }


class ConsistencyChecker:
    def check(
        self,
        context: ThesisContext,
        chapter_texts: Mapping[str, str] | None = None,
        *,
        terminology: Mapping[str, object] | None = None,
        citation_keys: object | None = None,
        research_questions: object = (),
    ) -> ConsistencyReport:
        if not isinstance(context, ThesisContext):
            raise TypeError("context must be a ThesisContext")
        if chapter_texts is None:
            texts: dict[str, str] = {}
        elif not isinstance(chapter_texts, Mapping):
            raise TypeError("chapter_texts must be a mapping of chapter titles to text")
        else:
            texts = {_text(title, "chapter title"): _text(text, "chapter text", required=False) for title, text in chapter_texts.items()}

        terminology_issues = self._terminology(texts, terminology)
        citation_issues = self._citations(context, citation_keys, texts)
        chapter_issues = self._chapters(context, texts)
        question_issues = self._questions(texts, research_questions)
        return ConsistencyReport(terminology_issues, citation_issues, chapter_issues, question_issues)

    @staticmethod
    def _terminology(texts: Mapping[str, str], terminology: Mapping[str, object] | None) -> tuple[ConsistencyIssue, ...]:
        if terminology is None:
            return ()
        if not isinstance(terminology, Mapping):
            raise TypeError("terminology must map canonical terms to variants")
        issues: list[ConsistencyIssue] = []
        for canonical, raw_variants in sorted(terminology.items(), key=lambda item: str(item[0]).casefold()):
            preferred = _text(canonical, "canonical term")
            variants = _strings(raw_variants, "term variants")
            for variant in sorted(set(variants), key=str.casefold):
                locations = tuple(title for title, text in texts.items() if re.search(rf"(?<!\w){re.escape(variant)}(?!\w)", text, re.IGNORECASE))
                if locations and variant.casefold() != preferred.casefold():
                    issues.append(ConsistencyIssue("nonpreferred_term", f"Use preferred term '{preferred}' instead of '{variant}'.", locations))
        return tuple(issues)

    @staticmethod
    def _citations(
        context: ThesisContext,
        citation_keys: object | None,
        texts: Mapping[str, str],
    ) -> tuple[ConsistencyIssue, ...]:
        issues: list[ConsistencyIssue] = []
        if citation_keys is not None:
            available = set(_strings(citation_keys, "citation_keys"))
            issues.extend(
                ConsistencyIssue("missing_citation_record", f"Citation '{key}' has no matching reference record.")
                for key in context.references
                if key not in available
            )
        declared = set(context.references)
        cited_locations: dict[str, set[str]] = {}
        for title, text in texts.items():
            for match in _LATEX_CITATION.finditer(text):
                for raw_key in match.group("keys").split(","):
                    key = raw_key.strip()
                    if key:
                        cited_locations.setdefault(key, set()).add(title)
        issues.extend(
            ConsistencyIssue(
                "missing_reference",
                f"Citation marker '{key}' is absent from the thesis reference context.",
                tuple(locations),
            )
            for key, locations in sorted(cited_locations.items())
            if key not in declared
        )
        return tuple(issues)

    @staticmethod
    def _chapters(context: ThesisContext, texts: Mapping[str, str]) -> tuple[ConsistencyIssue, ...]:
        issues: list[ConsistencyIssue] = []
        declared = {title.casefold() for title in context.chapters}
        for title in texts:
            if declared and title.casefold() not in declared:
                issues.append(ConsistencyIssue("undeclared_chapter", f"Chapter '{title}' is not present in the thesis context.", (title,)))
        if context.sections and not context.chapters:
            issues.append(ConsistencyIssue("orphan_sections", "Sections exist without a declared chapter."))
        if context.progress > 0 and not context.chapters:
            issues.append(ConsistencyIssue("progress_without_chapters", "Progress exists without a declared chapter."))
        if (context.references or context.figures or context.tables) and not context.chapters:
            issues.append(ConsistencyIssue("content_without_chapters", "Referenced thesis content exists without a declared chapter."))
        return tuple(issues)

    @staticmethod
    def _questions(texts: Mapping[str, str], research_questions: object) -> tuple[ConsistencyIssue, ...]:
        questions = _strings(research_questions, "research_questions")
        if not questions:
            return ()
        combined = " ".join(texts.values()).casefold()
        issues: list[ConsistencyIssue] = []
        stop = {"about", "does", "from", "have", "that", "the", "this", "what", "when", "where", "which", "with"}
        for index, question in enumerate(questions, start=1):
            keywords = {word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z-]{3,}", question) if word.casefold() not in stop}
            if not keywords:
                issues.append(ConsistencyIssue("research_question_incomplete", f"Research question {index} has no substantive keywords."))
            elif not any(re.search(rf"\b{re.escape(word)}\b", combined) for word in keywords):
                issues.append(ConsistencyIssue("research_question_unaddressed", f"Research question {index} has no keyword alignment with supplied chapters."))
        return tuple(issues)


def check_consistency(
    context: ThesisContext,
    chapter_texts: Mapping[str, str] | None = None,
    **options,
) -> ConsistencyReport:
    return ConsistencyChecker().check(context, chapter_texts, **options)
