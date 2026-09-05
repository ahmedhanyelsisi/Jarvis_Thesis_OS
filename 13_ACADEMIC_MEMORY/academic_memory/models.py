from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

@dataclass(frozen=True)
class MemoryEvent:
    event_id: str
    session_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]

@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str
    session_id: str
    context: str
    feedback_text: str
    timestamp: str

@dataclass(frozen=True)
class AgentPerformance:
    agent_role: str
    task_type: str
    success_rate: float
    total_executions: int
    average_duration_sec: float

@dataclass(frozen=True)
class WorkflowOutcome:
    workflow_id: str
    status: str
    steps_completed: int
    human_interventions: int

@dataclass(frozen=True)
class ResearcherProfile:
    researcher_id: str
    preferred_tone: str
    formatting_rules: List[str]
    supervisor_constraints: List[str]

@dataclass(frozen=True)
class LearningPattern:
    pattern_id: str
    topic: str
    pattern_description: str
    confidence: float  # 0.0 to 1.0 scoring as requested
