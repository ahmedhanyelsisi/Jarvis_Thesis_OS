import dataclasses
from typing import Tuple, Dict

@dataclasses.dataclass(frozen=True)
class ResearchPaper:
    paper_id: str
    title: str
    authors: Tuple[str, ...]
    abstract: str
    publication_year: int
    doi: str
    sections: Dict[str, str]
    metadata: Dict[str, str]

@dataclasses.dataclass(frozen=True)
class CitationNode:
    paper_id: str
    cited_papers: Tuple[str, ...]
    references: Tuple[str, ...]

@dataclasses.dataclass(frozen=True)
class ResearchGap:
    description: str
    supporting_papers: Tuple[str, ...]
    confidence: float

@dataclasses.dataclass(frozen=True)
class MethodologyProfile:
    approach: str
    dataset: str
    method: str
    limitations: str
