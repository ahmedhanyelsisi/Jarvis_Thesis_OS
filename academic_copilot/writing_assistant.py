"""Rule-bound academic writing diagnostics that never generate prose."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re


_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
_SENTENCE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
_CITATION = re.compile(r"\\(?:cite|citep|citet|textcite|parencite)\*?(?:\[[^\]]*\]){0,2}\{[^{}]+\}|\([A-Z][A-Za-z-]+(?: et al\.)?,? \d{4}[a-z]?\)")
_STOP_WORDS = frozenset({"about", "after", "also", "and", "are", "been", "being", "between", "but", "for", "from", "has", "have", "into", "its", "that", "the", "their", "these", "this", "those", "through", "was", "were", "which", "with"})


def _text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    normalized = " ".join(value.split()).strip()
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _strings(values: object, name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"{name} must be an iterable of strings")
    try:
        result = tuple(_text(value, name) for value in values)  # type: ignore[arg-type]
    except TypeError as error:
        if str(error).startswith(name):
            raise
        raise TypeError(f"{name} must be an iterable of strings") from error
    return tuple(sorted(set(result), key=str.casefold))


@dataclass(frozen=True, order=True)
class WritingRecommendation:
    code: str
    message: str
    priority: str = "medium"

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "code"))
        object.__setattr__(self, "message", _text(self.message, "message"))
        if self.priority not in {"low", "medium", "high"}:
            raise ValueError("priority must be low, medium, or high")

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "priority": self.priority}


@dataclass(frozen=True)
class ParagraphAnalysis:
    word_count: int
    sentence_count: int
    citation_count: int
    average_sentence_length: float
    issue_codes: tuple[str, ...] = ()
    recommendations: tuple[WritingRecommendation, ...] = ()

    def __post_init__(self) -> None:
        for name in ("word_count", "sentence_count", "citation_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if isinstance(self.average_sentence_length, bool) or not isinstance(self.average_sentence_length, (int, float)) or self.average_sentence_length < 0:
            raise ValueError("average_sentence_length must be non-negative")
        object.__setattr__(self, "average_sentence_length", round(float(self.average_sentence_length), 2))
        object.__setattr__(self, "issue_codes", _strings(self.issue_codes, "issue_codes"))
        recommendations = tuple(self.recommendations)
        if not all(isinstance(item, WritingRecommendation) for item in recommendations):
            raise TypeError("recommendations must contain WritingRecommendation values")
        object.__setattr__(self, "recommendations", tuple(sorted(recommendations)))

    def to_dict(self) -> dict[str, object]:
        return {
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "citation_count": self.citation_count,
            "average_sentence_length": self.average_sentence_length,
            "issue_codes": list(self.issue_codes),
            "recommendations": [item.to_dict() for item in self.recommendations],
        }


@dataclass(frozen=True)
class StructureSuggestion:
    section_type: str
    recommended_components: tuple[str, ...]
    missing_components: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_type", _text(self.section_type, "section_type").casefold())
        object.__setattr__(self, "recommended_components", _strings(self.recommended_components, "recommended_components"))
        object.__setattr__(self, "missing_components", _strings(self.missing_components, "missing_components"))

    def to_dict(self) -> dict[str, object]:
        return {"section_type": self.section_type, "recommended_components": list(self.recommended_components), "missing_components": list(self.missing_components)}


@dataclass(frozen=True, order=True)
class RepetitionFinding:
    term: str
    count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "term", _text(self.term, "term").casefold())
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 2:
            raise ValueError("count must be an integer of at least two")

    def to_dict(self) -> dict[str, object]:
        return {"term": self.term, "count": self.count}


@dataclass(frozen=True)
class RepetitionReport:
    repeated_terms: tuple[RepetitionFinding, ...] = ()

    def __post_init__(self) -> None:
        items = tuple(self.repeated_terms)
        if not all(isinstance(item, RepetitionFinding) for item in items):
            raise TypeError("repeated_terms must contain RepetitionFinding values")
        object.__setattr__(self, "repeated_terms", tuple(sorted(items, key=lambda item: (-item.count, item.term))))

    def to_dict(self) -> dict[str, object]:
        return {"repeated_terms": [item.to_dict() for item in self.repeated_terms]}


@dataclass(frozen=True)
class ArgumentAssessment:
    present_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    recommendations: tuple[WritingRecommendation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "present_components", _strings(self.present_components, "present_components"))
        object.__setattr__(self, "missing_components", _strings(self.missing_components, "missing_components"))
        recommendations = tuple(self.recommendations)
        if not all(isinstance(item, WritingRecommendation) for item in recommendations):
            raise TypeError("recommendations must contain WritingRecommendation values")
        object.__setattr__(self, "recommendations", tuple(sorted(recommendations)))

    def to_dict(self) -> dict[str, object]:
        return {"present_components": list(self.present_components), "missing_components": list(self.missing_components), "recommendations": [item.to_dict() for item in self.recommendations]}


_STRUCTURES = {
    "introduction": ("context", "problem statement", "research questions", "scope", "contribution"),
    "literature review": ("search scope", "thematic synthesis", "critical comparison", "research gap"),
    "methodology": ("research design", "data source", "procedure", "analysis method", "validity and ethics"),
    "results": ("analysis overview", "findings by research question", "tables or figures", "summary"),
    "discussion": ("interpretation", "comparison with literature", "implications", "limitations"),
    "conclusion": ("answer to research questions", "contributions", "limitations", "future work"),
}


def analyze_paragraph(paragraph: str) -> ParagraphAnalysis:
    text = _text(paragraph, "paragraph")
    words = _WORD.findall(text)
    sentences = [match.group(0) for match in _SENTENCE.finditer(text) if match.group(0).strip()]
    citations = _CITATION.findall(text)
    issues: list[str] = []
    recommendations: list[WritingRecommendation] = []
    average = len(words) / len(sentences) if sentences else 0.0
    if len(words) < 20:
        issues.append("underdeveloped_paragraph")
        recommendations.append(WritingRecommendation("develop_argument", "Add claim, evidence, and interpretation components.", "high"))
    if average > 30:
        issues.append("long_sentences")
        recommendations.append(WritingRecommendation("shorten_sentences", "Split sentences longer than the academic readability threshold."))
    if len(words) >= 40 and not citations:
        issues.append("citation_support_absent")
        recommendations.append(WritingRecommendation("add_evidence_reference", "Link externally verifiable claims to an existing source.", "high"))
    repetition = detect_repetition(text)
    if repetition.repeated_terms:
        issues.append("lexical_repetition")
        recommendations.append(WritingRecommendation("reduce_repetition", "Review repeated content words for necessary variation.", "low"))
    return ParagraphAnalysis(len(words), len(sentences), len(citations), average, tuple(issues), tuple(recommendations))


def suggest_structure(section_type: str, existing_components: object = ()) -> StructureSuggestion:
    normalized = _text(section_type, "section_type").casefold().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    if normalized not in _STRUCTURES:
        raise ValueError(f"unsupported section_type: {normalized}")
    existing = {item.casefold() for item in _strings(existing_components, "existing_components")}
    recommended = _STRUCTURES[normalized]
    missing = tuple(component for component in recommended if component.casefold() not in existing)
    return StructureSuggestion(normalized, recommended, missing)


def detect_repetition(text: str, *, threshold: int = 3) -> RepetitionReport:
    normalized = _text(text, "text")
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 2:
        raise ValueError("threshold must be an integer of at least two")
    words = [word.casefold() for word in _WORD.findall(normalized)]
    counts = Counter(word for word in words if len(word) >= 4 and word not in _STOP_WORDS)
    return RepetitionReport(tuple(RepetitionFinding(term, count) for term, count in counts.items() if count >= threshold))


def identify_missing_argument(paragraph: str) -> ArgumentAssessment:
    text = _text(paragraph, "paragraph")
    lowered = text.casefold()
    components = {
        "claim": bool(re.search(r"\b(argue|claim|demonstrate|indicate|propose|show|suggest)\w*\b", lowered)),
        "evidence": bool(_CITATION.search(text) or re.search(r"\b(data|evidence|result|finding)s?\b", lowered)),
        "reasoning": bool(re.search(r"\b(because|consequently|therefore|thus|which means)\b", lowered)),
        "qualification": bool(re.search(r"\b(although|however|limitation|may|might|within)\b", lowered)),
    }
    present = tuple(name for name, found in components.items() if found)
    missing = tuple(name for name, found in components.items() if not found)
    messages = {
        "claim": "State one explicit, bounded claim.",
        "evidence": "Attach evidence or an existing citation to the claim.",
        "reasoning": "Explain how the evidence supports the claim.",
        "qualification": "State the boundary or limitation of the claim.",
    }
    recommendations = tuple(WritingRecommendation(f"add_{name}", messages[name], "high" if name in {"claim", "evidence"} else "medium") for name in missing)
    return ArgumentAssessment(present, missing, recommendations)
