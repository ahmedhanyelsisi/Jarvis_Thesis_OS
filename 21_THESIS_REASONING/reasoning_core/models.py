import dataclasses
from typing import Tuple, Optional
from enum import Enum

class EvidenceSource(Enum):
    RESEARCH = "research"
    THESIS = "thesis"
    USER = "user"

@dataclasses.dataclass(frozen=True)
class Evidence:
    source: EvidenceSource
    source_id: str
    content: str

@dataclasses.dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    evidence: Tuple[Evidence, ...]

@dataclasses.dataclass(frozen=True)
class ReasoningConfidence:
    score: float  # 0.0 to 1.0
    factors: Tuple[str, ...]

@dataclasses.dataclass(frozen=True)
class Argument:
    argument_id: str
    claims: Tuple[Claim, ...]
    conclusion: str
    strength: float
    confidence: ReasoningConfidence

@dataclasses.dataclass(frozen=True)
class Contradiction:
    description: str
    conflicting_claims: Tuple[Claim, ...]
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"

@dataclasses.dataclass(frozen=True)
class ReasoningResult:
    arguments: Tuple[Argument, ...]
    contradictions: Tuple[Contradiction, ...]
    synthesis_summary: str
