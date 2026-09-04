from typing import Protocol, Any, Dict, runtime_checkable
from .models import AgentTask, AgentResult

@runtime_checkable
class IAgent(Protocol):
    """Immutable IAgent contract required by Stone 17."""
    
    @property
    def name(self) -> str: ...
    
    @property
    def role(self) -> str: ...
    
    def execute(self, task: AgentTask, context: Any) -> AgentResult: ...
    
    def status(self) -> str: ...
