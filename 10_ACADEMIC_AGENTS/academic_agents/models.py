from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import uuid

@dataclass(frozen=True)
class AgentTask:
    task_id: str
    agent_name: str
    objective: str
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: str = "PENDING"

@dataclass(frozen=True)
class AgentResult:
    success: bool
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: list = field(default_factory=list)

@dataclass(frozen=True)
class AgentExecutionPolicy:
    max_steps: int = 20
    max_messages: int = 50
    timeout_seconds: int = 300
    max_tokens: int = 16000
