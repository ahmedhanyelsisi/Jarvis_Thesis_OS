"""Persistent memory for decisions, strategies, and workflow experience."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

from .models import ExecutionStrategy, WorkflowState


class ReasoningMemory:
    """Store reasoning history separately from the Stone 4 knowledge store."""

    def __init__(self, path: str | Path = ".jarvis/reasoning_memory.json") -> None:
        self.path = Path(path)
        self._lock = RLock()

    def record_workflow(
        self,
        state: WorkflowState,
        strategy: ExecutionStrategy | None = None,
    ) -> None:
        """Persist a workflow result and its selected strategy."""

        with self._lock:
            data = self._load()
            record = state.to_dict()
            if strategy is not None:
                record["strategy"] = strategy.to_dict()
            data["previous_workflows"].append(record)
            data["execution_history"].append(
                {
                    "workflow_id": state.workflow_id,
                    "completed": list(state.completed_tasks),
                    "failed": list(state.failed_tasks),
                    "skipped": list(state.skipped_tasks),
                }
            )
            if strategy is not None and not state.failed_tasks:
                successful = {
                    "task_type": strategy.task_type,
                    "steps": strategy.steps,
                    "successful_agents": strategy.required_agents,
                }
                if successful not in data["successful_strategies"]:
                    data["successful_strategies"].append(successful)
            self._save(data)

    def set_preference(self, name: str, value: Any) -> None:
        """Persist one explicit user preference."""

        if not name.strip():
            raise ValueError("Preference name cannot be empty.")
        with self._lock:
            data = self._load()
            data["user_preferences"][name] = value
            self._save(data)

    def store_workflow(
        self,
        state: WorkflowState,
        strategy: ExecutionStrategy | None = None,
    ) -> None:
        """Alias for callers that use storage-oriented terminology."""

        self.record_workflow(state, strategy)

    def get_preference(self, name: str, default: Any = None) -> Any:
        """Retrieve a user preference."""

        return self._load()["user_preferences"].get(name, default)

    def recall(self) -> dict[str, Any]:
        """Return all stored reasoning experience."""

        return self._load()

    def _load(self) -> dict[str, Any]:
        empty = {
            "previous_workflows": [],
            "successful_strategies": [],
            "user_preferences": {},
            "execution_history": [],
        }
        if not self.path.exists():
            return empty
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Reasoning memory is unreadable: {self.path}") from error
        for key, default in empty.items():
            raw.setdefault(key, default)
        return raw

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        temporary.replace(self.path)
