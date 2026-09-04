import json
import os
import dataclasses
import re
from pathlib import Path
from typing import Optional, Dict, Any
from .models import WorkflowState, WorkflowNode, Checkpoint
from .exceptions import WorkflowPersistenceError

class WorkflowPersistence:
    """Handles JSON serialization and local persistence for workflows."""
    
    def __init__(self, workspace_root: str):
        self._db_path = Path(workspace_root) / ".jarvis" / "workflows"
        self._db_path.mkdir(parents=True, exist_ok=True)
        
    def _to_dict(self, obj: Any) -> Any:
        if dataclasses.is_dataclass(obj):
            return {f.name: self._to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
        elif isinstance(obj, dict):
            return {k: self._to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._to_dict(x) for x in obj]
        else:
            return obj

    def _from_dict_node(self, data: Dict[str, Any]) -> WorkflowNode:
        return WorkflowNode(**data)

    def _from_dict_checkpoint(self, data: Optional[Dict[str, Any]]) -> Optional[Checkpoint]:
        if not data:
            return None
        return Checkpoint(**data)

    def _from_dict_state(self, data: Dict[str, Any]) -> WorkflowState:
        nodes = {k: self._from_dict_node(v) for k, v in data.get("nodes", {}).items()}
        cp = self._from_dict_checkpoint(data.get("pending_checkpoint"))
        
        return WorkflowState(
            workflow_id=data["workflow_id"],
            workflow_type=data["workflow_type"],
            status=data["status"],
            current_node=data.get("current_node"),
            nodes=nodes,
            completed_nodes=tuple(data.get("completed_nodes", [])),
            pending_checkpoint=cp,
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            history=tuple(data.get("history", []))
        )

    def _validate_workflow_id(self, workflow_id: str) -> None:
        if not workflow_id or "\x00" in workflow_id:
            raise WorkflowPersistenceError("Invalid workflow ID: null bytes not allowed.")
        if not re.match(r'^[\w\-]+$', workflow_id):
            raise WorkflowPersistenceError(f"Invalid workflow ID: {workflow_id}. Only alphanumeric, hyphen, and underscore allowed.")

    def _get_safe_path(self, workflow_id: str) -> Path:
        self._validate_workflow_id(workflow_id)
        # We append prefix just to be safe
        filename = f"workflow_{workflow_id}.json"
        file_path = self._db_path / filename
        
        try:
            resolved = file_path.resolve()
            db_resolved = self._db_path.resolve()
            if not resolved.is_relative_to(db_resolved):
                raise WorkflowPersistenceError("Path traversal attempt blocked.")
        except Exception as e:
            raise WorkflowPersistenceError(f"Path resolution error: {e}")
            
        return file_path

    def save(self, state: WorkflowState) -> None:
        file_path = self._get_safe_path(state.workflow_id)
        temp_path = file_path.with_suffix(".json.tmp")
        
        data = self._to_dict(state)
        
        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic replace
            temp_path.replace(file_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise WorkflowPersistenceError(f"Failed to persist workflow {state.workflow_id}: {e}")

    def load(self, workflow_id: str) -> Optional[WorkflowState]:
        file_path = self._get_safe_path(workflow_id)
        
        if not file_path.exists():
            return None
            
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return self._from_dict_state(data)
        except json.JSONDecodeError:
            raise WorkflowPersistenceError(f"Corrupted workflow state JSON for {workflow_id}.")
        except Exception as e:
            raise WorkflowPersistenceError(f"Failed to load workflow state for {workflow_id}: {e}")
