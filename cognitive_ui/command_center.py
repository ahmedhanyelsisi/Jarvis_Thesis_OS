"""Command-to-kernel adapter for the Jarvis cognitive UI."""

from __future__ import annotations

import re
import time
from typing import Any, Protocol

from .event_bus import (
    AGENT_COMPLETED,
    AGENT_STARTED,
    COMMAND_RECEIVED,
    MEMORY_UPDATED,
    RESPONSE_READY,
    WORKFLOW_STARTED,
    EventBus,
)
from .session_state import SessionState
from .dashboard_metrics import DashboardMetrics
from .security import validate_command
from .session_store import SessionStore


class JarvisKernel(Protocol):
    """Only the public kernel surface consumed by the command center."""

    def process_request(self, request: str) -> Any: ...

    def process_workflow(self, request: str, evaluate: bool = True) -> Any: ...

    def get_system_status(self) -> dict[str, Any]: ...


class CommandCenter:
    """Receive commands, invoke Jarvis, and project observable UI state."""

    def __init__(
        self,
        jarvis: JarvisKernel,
        session_state: SessionState | None = None,
        event_bus: EventBus | None = None,
        session_store: SessionStore | None = None,
        metrics: DashboardMetrics | None = None,
    ) -> None:
        self.jarvis = jarvis
        self.session_state = session_state or SessionState()
        self.event_bus = event_bus or EventBus()
        self.session_store = session_store
        self.metrics = metrics or DashboardMetrics()

    @property
    def state(self) -> SessionState:
        """Short alias useful to interactive interface adapters."""

        return self.session_state

    def send_command(
        self,
        command: str,
        *,
        workflow: bool = False,
        evaluate: bool = True,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Send one validated command through the existing Jarvis APIs."""

        validation = validate_command(command, confirmed=confirmed)
        if not validation.valid and not validation.requires_confirmation:
            raise ValueError(validation.reason or "Invalid command.")
        if not isinstance(command, str):
            raise ValueError(validation.reason or "Invalid command.")
        command = command.strip()
        mode = "workflow" if workflow else "request"
        self.session_state.begin_task(command, workflow=workflow)
        self.event_bus.emit(
            COMMAND_RECEIVED,
            {"command": command, "mode": mode},
            source="command_center",
        )
        if not validation.valid:
            response = {"error": validation.reason, "security": validation.to_dict()}
            self.session_state.finish_task(response, failed=True)
            self.metrics.record_request(workflow=workflow, successful=False)
            result = self._structured_response("blocked", command, mode, response)
            self.event_bus.emit(
                RESPONSE_READY,
                {"status": "blocked", "command": command},
                source="security",
            )
            self._persist_session()
            return result
        if workflow:
            self.event_bus.emit(
                WORKFLOW_STARTED,
                {"command": command},
                source="command_center",
            )

        started = time.perf_counter()
        try:
            if workflow:
                kernel_response = self.jarvis.process_workflow(
                    command,
                    evaluate=evaluate,
                )
            else:
                kernel_response = self.jarvis.process_request(command)
        except Exception as error:
            error_response = {
                "error": str(error),
                "exception": type(error).__name__,
            }
            self.session_state.finish_task(error_response, failed=True)
            self.metrics.record_request(
                workflow=workflow,
                successful=False,
                duration=time.perf_counter() - started,
            )
            result = self._structured_response(
                "failed", command, mode, error_response
            )
            self._persist_session()
            self.event_bus.emit(
                RESPONSE_READY,
                {"status": "failed", "command": command},
                source="command_center",
            )
            return result

        self._project_kernel_response(command, kernel_response, workflow=workflow)
        failed = self._response_failed(kernel_response)
        self.session_state.finish_task(kernel_response, failed=failed)
        status = "failed" if failed else "completed"
        self.metrics.record_request(
            workflow=workflow,
            successful=not failed,
            duration=time.perf_counter() - started,
            active_agents=len(self.session_state.active_agents),
        )
        result = self._structured_response(status, command, mode, kernel_response)
        self._persist_session()
        self.event_bus.emit(
            RESPONSE_READY,
            {"status": status, "command": command},
            source="command_center",
        )
        return result

    process_command = send_command
    execute = send_command

    def get_system_status(self) -> dict[str, Any]:
        """Return the kernel's status without reaching into its managers."""

        return dict(self.jarvis.get_system_status())

    def _structured_response(
        self,
        status: str,
        command: str,
        mode: str,
        kernel_response: Any,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "command": command,
            "mode": mode,
            "response": kernel_response,
            "intent": self.extract_intent(command),
            "session": self.session_state.snapshot(),
            "system_status": self.get_system_status(),
            "metrics": self.metrics.to_dict(),
        }

    def _persist_session(self) -> None:
        if self.session_store is not None:
            self.session_store.save_session(self.session_state)

    def get_metrics(self) -> dict[str, object]:
        return self.metrics.to_dict()

    @staticmethod
    def extract_intent(command: str) -> dict[str, str | None]:
        """Extract a small deterministic intent/target/agent projection."""

        text = re.sub(r"^\s*jarvis[\s,;:!-]*", "", str(command), flags=re.IGNORECASE).strip()
        chapter = re.search(r"\b(chapter\s+[\w.-]+)\b", text, flags=re.IGNORECASE)
        target = chapter.group(1).lower() if chapter else None
        lowered = text.lower()
        if re.search(r"\bcontinue\b", lowered):
            return {"intent": "continue_writing", "target": target, "agent": "latex_agent"}
        if re.search(r"\b(review|critique|check|improve)\b", lowered):
            return {"intent": "review", "target": target, "agent": "reviewer_agent"}
        if re.search(r"\b(latex|equation|compile)\b", lowered):
            return {"intent": "latex", "target": target, "agent": "latex_agent"}
        if re.search(r"\b(write|draft|create)\b", lowered):
            return {"intent": "write", "target": target, "agent": "thesis_writer_agent"}
        return {"intent": "general_request", "target": target, "agent": None}

    def _project_kernel_response(
        self,
        command: str,
        response: Any,
        *,
        workflow: bool,
    ) -> None:
        if not isinstance(response, dict):
            return
        if workflow:
            workflow_data = response.get("workflow")
            if isinstance(workflow_data, dict):
                self.session_state.update_workflow(workflow_data)
            for task in response.get("tasks", []):
                if not isinstance(task, dict) or not task.get("required_agent"):
                    continue
                failed = str(task.get("status", "")).upper() in {
                    "FAILED",
                    "SKIPPED",
                }
                self._record_agent(
                    str(task["required_agent"]),
                    str(task.get("description", command)),
                    failed=failed,
                )
            if (
                not self._response_failed(response)
                and isinstance(workflow_data, dict)
                and not workflow_data.get("skipped_tasks")
                and self.get_system_status().get("memory") == "active"
            ):
                self.event_bus.emit(
                    MEMORY_UPDATED,
                    {"source": "workflow", "command": command},
                    source="command_center",
                )
            return
        agent_name = response.get("agent")
        if agent_name:
            self._record_agent(
                str(agent_name),
                command,
                failed=self._response_failed(response),
            )

    def _record_agent(self, name: str, task: str, *, failed: bool) -> None:
        self.session_state.start_agent(name, task)
        self.event_bus.emit(
            AGENT_STARTED,
            {"agent": name, "task": task},
            source="command_center",
        )
        self.session_state.complete_agent(name, failed=failed)
        self.event_bus.emit(
            AGENT_COMPLETED,
            {"agent": name, "status": "failed" if failed else "completed"},
            source="command_center",
        )

    @staticmethod
    def _response_failed(response: Any) -> bool:
        if not isinstance(response, dict):
            return False
        if str(response.get("status", "")).lower() in {"failed", "error"}:
            return True
        workflow = response.get("workflow")
        return isinstance(workflow, dict) and bool(workflow.get("failed_tasks"))
