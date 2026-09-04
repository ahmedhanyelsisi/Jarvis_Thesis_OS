import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from latex_engine.models import BuildRequest, BuildResult

class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass(frozen=True, order=True)
class BuildTask:
    """Immutable representation of a build job. Orders by priority (lower is faster), then creation time."""
    priority: int = field(compare=True)
    created_at: float = field(compare=True)
    
    task_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    request: BuildRequest = field(compare=False, default=None)  # Must be provided
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    completed_at: Optional[float] = field(compare=False, default=None)
    result: Optional[BuildResult] = field(compare=False, default=None)
    error_message: Optional[str] = field(compare=False, default=None)

    def transition_to(self, new_status: TaskStatus, **kwargs) -> 'BuildTask':
        """Safely transitions state and returns a new immutable BuildTask."""
        from .exceptions import InvalidStateTransitionError
        from dataclasses import replace
        
        valid_transitions = {
            TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.FAILED},
            TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
            TaskStatus.COMPLETED: set(),
            TaskStatus.FAILED: set()
        }
        
        if new_status not in valid_transitions[self.status]:
            raise InvalidStateTransitionError(f"Cannot transition task from {self.status.name} to {new_status.name}")
            
        return replace(self, status=new_status, **kwargs)

@dataclass(frozen=True)
class BuildHistoryEntry:
    """Immutable representation of historical build artifacts/telemetry."""
    task_id: str
    status: TaskStatus
    duration_seconds: float
    completed_at: float
    success: bool
    error_message: Optional[str] = None
