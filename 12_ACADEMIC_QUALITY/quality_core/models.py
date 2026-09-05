import dataclasses
from typing import Dict, Tuple, Optional

@dataclasses.dataclass(frozen=True)
class Metric:
    name: str
    score: float  # 0.0 to 10.0
    weight: float
    reasoning: str

@dataclasses.dataclass(frozen=True)
class RevisionTask:
    task_id: str
    description: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    target_metric: str

@dataclasses.dataclass(frozen=True)
class QualityScore:
    overall_score: float
    metrics: Tuple[Metric, ...]

@dataclasses.dataclass(frozen=True)
class QualityReport:
    report_id: str
    workflow_id: str
    node_id: str
    score: QualityScore
    tasks: Tuple[RevisionTask, ...]
    recommendation: str  # "APPROVE", "REVISE", "REJECT"
    timestamp: float
