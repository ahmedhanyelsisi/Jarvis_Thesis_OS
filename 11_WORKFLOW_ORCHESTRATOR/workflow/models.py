from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time

@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    reason: str
    requested_by: str
    approval_status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    agent_type: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300

@dataclass(frozen=True)
class WorkflowState:
    workflow_id: str
    workflow_type: str
    status: str = "PENDING"  # PENDING, RUNNING, PAUSED, COMPLETED, FAILED
    current_node: Optional[str] = None
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    completed_nodes: tuple[str, ...] = field(default_factory=tuple)
    pending_checkpoint: Optional[Checkpoint] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    history: tuple[str, ...] = field(default_factory=tuple)
