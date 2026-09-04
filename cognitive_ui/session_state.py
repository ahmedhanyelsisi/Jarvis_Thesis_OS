"""Thread-safe UI session state independent of kernel reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any
from uuid import uuid4

from .dashboard_models import AgentStatus, WorkflowStatus, utc_now


@dataclass
class SessionState:
    """Mutable state projected to current and future Jarvis interfaces."""

    active_session: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=utc_now)
    current_task: str | None = None
    workflow_status: WorkflowStatus = field(default_factory=WorkflowStatus)
    last_response: Any = None
    active_agents: dict[str, AgentStatus] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    @property
    def session_id(self) -> str:
        """Compatibility-friendly alias for the active session identifier."""

        return self.active_session

    def begin_task(self, command: str, *, workflow: bool = False) -> None:
        with self._lock:
            self.current_task = command
            self.last_response = None
            self.active_agents.clear()
            self.workflow_status = WorkflowStatus(
                status="running" if workflow else "idle"
            )

    def start_agent(self, name: str, task: str | None = None) -> AgentStatus:
        with self._lock:
            status = AgentStatus(
                name=name,
                status="running",
                current_task=task,
                started_at=utc_now(),
            )
            self.active_agents[name] = status
            return status

    def complete_agent(self, name: str, *, failed: bool = False) -> AgentStatus:
        with self._lock:
            status = self.active_agents.get(name) or AgentStatus(name=name)
            status.status = "failed" if failed else "completed"
            status.completed_at = utc_now()
            self.active_agents.pop(name, None)
            return status

    def update_workflow(self, workflow: dict[str, Any]) -> None:
        with self._lock:
            completed = list(workflow.get("completed_tasks", []))
            failed = list(workflow.get("failed_tasks", []))
            skipped = list(workflow.get("skipped_tasks", []))
            if failed:
                status = "failed"
            elif workflow.get("current_task"):
                status = "running"
            else:
                status = "completed"
            self.workflow_status = WorkflowStatus(
                status=status,
                workflow_id=workflow.get("workflow_id"),
                current_task=workflow.get("current_task"),
                completed_tasks=completed,
                failed_tasks=failed,
                skipped_tasks=skipped,
                total_tasks=len(completed) + len(failed) + len(skipped),
            )

    def finish_task(self, response: Any, *, failed: bool = False) -> None:
        with self._lock:
            self.last_response = response
            self.current_task = None
            if self.workflow_status.status == "running":
                self.workflow_status.status = "failed" if failed else "completed"

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active_session": self.active_session,
                "started_at": self.started_at.isoformat(),
                "current_task": self.current_task,
                "workflow_status": self.workflow_status.to_dict(),
                "last_response": self.last_response,
                "active_agents": {
                    name: status.to_dict()
                    for name, status in self.active_agents.items()
                },
            }
