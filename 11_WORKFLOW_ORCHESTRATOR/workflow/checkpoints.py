from enum import Enum
import uuid
from typing import Dict, Any

from .models import Checkpoint

class CheckpointType(str, Enum):
    A_STRUCTURAL = "structural_change"
    B_WRITE_DISK = "write_to_disk"
    C_FINAL_DECISION = "final_academic_decision"

class CheckpointManager:
    """Manages the creation and resolution of Human-in-the-Loop checkpoints."""
    
    @staticmethod
    def create_checkpoint(reason: CheckpointType, requested_by: str, metadata: Dict[str, Any] = None) -> Checkpoint:
        return Checkpoint(
            checkpoint_id=str(uuid.uuid4()),
            reason=reason.value,
            requested_by=requested_by,
            approval_status="PENDING",
            metadata=metadata or {}
        )
