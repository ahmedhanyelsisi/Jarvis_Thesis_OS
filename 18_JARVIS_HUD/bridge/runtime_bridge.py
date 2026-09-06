"""Thread-safe, presentation-only adapter for the functional JARVIS HUD.

This module deliberately owns no authority.  QML can submit typed strings and
proposal identifiers only; this bridge forwards validated requests to the
frozen ChatManager, which remains the conversation and authorization boundary.
"""
from __future__ import annotations

import queue
import sys
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot
from .runtime_composition import LiveRuntimeComposition


ROOT = Path(__file__).resolve().parents[2]
CONVERSATION_ROOT = ROOT / "16_CONVERSATION_ENGINE"
if str(CONVERSATION_ROOT) not in sys.path:
    sys.path.insert(0, str(CONVERSATION_ROOT))

from conversation_core.chat_manager import ChatManager  # noqa: E402


TERMINAL_EVENTS = frozenset(
    {"approval_required", "approval_resolved", "cancelled", "error", "completed"}
)


@dataclass(frozen=True)
class HudEvent:
    schema_version: int
    sequence: int
    timestamp: float
    session_id: str
    workflow_id: str | None
    agent_id: str | None
    event_type: str
    provenance: str
    correlation_id: str
    redacted_payload: dict[str, Any]


class HudEventAdapter:
    """Bounded queue with progress coalescing; terminal/security events survive."""

    def __init__(self, maxsize: int = 128) -> None:
        self._queue: queue.Queue[HudEvent] = queue.Queue(maxsize=maxsize)
        self._terminal: deque[HudEvent] = deque()
        self._sequence = 0
        self._lock = threading.Lock()

    def normalize(self, event_type: str, *, session_id: str, correlation_id: str,
                  payload: dict[str, Any] | None = None, agent_id: str | None = None,
                  workflow_id: str | None = None, provenance: str = "hud_bridge") -> HudEvent:
        with self._lock:
            self._sequence += 1
            return HudEvent(1, self._sequence, time.time(), session_id, workflow_id,
                            agent_id, event_type, provenance, correlation_id, payload or {})

    def offer(self, event: HudEvent) -> bool:
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            if event.event_type in TERMINAL_EVENTS:
                # Security, terminal, and approval events must not be coalesced.
                # They are infrequent, so preserve them in a separate drain lane.
                with self._lock:
                    self._terminal.append(event)
                return True
            return True  # coalescible progress is represented by the latest view state

    def drain(self) -> list[HudEvent]:
        events: list[HudEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        with self._lock:
            events.extend(self._terminal)
            self._terminal.clear()
        return events


class RuntimeBridge(QObject):
    """Safe Qt-facing view model over the real local conversation service."""

    changed = Signal()
    _completed = Signal(object)
    _runtime_event = Signal(object)

    def __init__(self, *, prototype_mode: bool = False, chat: ChatManager | None = None,
                 live_runtime: bool = False) -> None:
        super().__init__()
        self._chat = chat or ChatManager()
        self._prototype_mode = prototype_mode
        self._events = HudEventAdapter()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jarvis-hud")
        self._messages: list[dict[str, str]] = []
        self._core_state = "IDLE"
        self._mission_stage = 0
        self._error = ""
        self._pending: dict[str, Any] | None = None
        self._resolved: set[str] = set()
        self._agents: dict[str, str] = {}
        self._terminal_workflows: set[str] = set()
        self._request_ids: set[str] = set()
        self._closed = False
        self._runtime: LiveRuntimeComposition | None = None
        self._runtime_status = "UNCONFIGURED"
        self._live_health: dict[str, str] = {}
        self._completed.connect(self._apply_completed)
        self._runtime_event.connect(self._apply_runtime_event)
        self._record("system", "Functional HUD connected to the local conversation service.")
        if live_runtime and not prototype_mode:
            self.startLiveRuntime()

    @Property(bool, constant=True)
    def prototypeMode(self) -> bool:  # QML naming intentionally matches its property.
        return self._prototype_mode

    @Property(str, notify=changed)
    def coreState(self) -> str:
        return self._core_state

    @Property(int, notify=changed)
    def missionStage(self) -> int:
        return self._mission_stage

    @Property("QVariantList", notify=changed)
    def messages(self) -> list[dict[str, str]]:
        return list(self._messages[-8:])

    @Property("QVariantList", notify=changed)
    def healthRows(self) -> list[dict[str, str]]:
        health = self._live_health
        return [
            {"label": "CONVERSATION", "value": "ONLINE", "tone": "#87dfbb"},
            {"label": "AUTHORIZATION", "value": "ONLINE", "tone": "#87dfbb"},
            {"label": "RUNTIME", "value": self._runtime_status, "tone": "#87dfbb" if self._runtime_status == "ONLINE" else "#f4b96b"},
            {"label": "EVENT BUS", "value": health.get("EventBus", "UNCONFIGURED"), "tone": "#87dfbb" if health.get("EventBus") == "ONLINE" else "#f4b96b"},
            {"label": "AGENTS", "value": health.get("AgentSandbox", "EVENTS UNAVAILABLE"), "tone": "#87dfbb" if health.get("AgentSandbox") == "ONLINE" else "#f4b96b"},
            {"label": "RESEARCH", "value": health.get("ResearchLayer", "UNCONFIGURED"), "tone": "#87dfbb" if health.get("ResearchLayer") == "ONLINE" else "#f4b96b"},
            {"label": "THESIS", "value": "ROOT NOT CONFIGURED", "tone": "#f4b96b"},
            {"label": "VOICE", "value": "SOFTWARE AVAILABLE", "tone": "#87bbff"},
            {"label": "WAKE", "value": "DISABLED", "tone": "#f4b96b"},
        ]

    @Property("QVariantMap", notify=changed)
    def approval(self) -> dict[str, Any]:
        return dict(self._pending or {})

    @Property("QVariantMap", notify=changed)
    def autonomy(self) -> dict[str, Any]:
        scopes = self._chat.auth_manager.scoped_manager.get_active_scopes()
        return {
            "mode": "AUTONOMOUS" if scopes else "CONTROLLED",
            "scopes": ", ".join(scopes) if scopes else "No active scopes",
            "session": self._chat.auth_manager.session_id,
        }

    @Property(str, notify=changed)
    def errorSummary(self) -> str:
        return self._error

    @Slot(str, result=str)
    def agentState(self, agent_id: str) -> str:
        return self._agents.get(agent_id.lower(), "DORMANT")

    @Slot(str)
    def submitText(self, text: str) -> None:
        if self._closed or not isinstance(text, str) or not text.strip() or len(text) > 4096:
            self._fail("Request rejected", "Enter a non-empty request up to 4096 characters.")
            return
        request_id = str(uuid.uuid4())
        if request_id in self._request_ids:
            self._fail("Duplicate request", "The same request cannot be submitted twice.")
            return
        self._request_ids.add(request_id)
        self._record("user", text.strip())
        self._core_state, self._mission_stage = "THINKING", 1
        self._emit("user_message_accepted", request_id, {"length": len(text.strip())})
        self.changed.emit()
        future = self._executor.submit(self._chat.handle_text, text.strip())
        future.add_done_callback(lambda completed: self._completed.emit(("text", request_id, completed)))

    @Slot(str)
    def approveProposal(self, proposal_id: str) -> None:
        pending = self._pending
        if not pending or proposal_id != pending.get("proposal_id") or proposal_id in self._resolved:
            self._fail("Approval rejected", "The proposal is stale, resolved, or does not match this session.")
            return
        if pending.get("session_id") != self._chat.auth_manager.session_id:
            self._fail("Approval rejected", "The proposal belongs to a different session.")
            return
        self._core_state = "WAITING_FOR_APPROVAL"
        self.changed.emit()
        future = self._executor.submit(self._chat.handle_text, f"approve {proposal_id}")
        future.add_done_callback(lambda completed: self._completed.emit(("approval", proposal_id, completed)))

    @Slot()
    def cancelCurrent(self) -> None:
        if self._pending is None:
            self._record("system", "No pending authorization request can be cancelled.")
            self.changed.emit()
            return
        self._chat.cancel(reset_session=False)
        if self._pending:
            self._resolved.add(str(self._pending["proposal_id"]))
        self._pending = None
        self._core_state, self._mission_stage = "IDLE", 0
        self._record("system", "Cancel requested through the local conversation service.")
        self._emit("cancelled", "cancel", {})
        self.changed.emit()

    @Slot()
    def close(self) -> None:
        if not self._closed:
            self._closed = True
            if self._runtime is not None:
                self._runtime.close()
            self._executor.shutdown(wait=False, cancel_futures=True)

    @Slot()
    def startLiveRuntime(self) -> None:
        if self._closed or self._runtime is not None:
            return
        self._runtime_status = "STARTING"
        self._runtime = LiveRuntimeComposition(
            session_id=self._chat.auth_manager.session_id,
            deliver_event=lambda event: self._runtime_event.emit(event),
        )
        self.changed.emit()
        future = self._executor.submit(self._runtime.start)
        future.add_done_callback(lambda completed: self._completed.emit(("runtime", "runtime-start", completed)))

    def _apply_completed(self, payload: object) -> None:
        kind, correlation_id, completed = payload
        try:
            reply = completed.result()
        except Exception as exc:  # presentation-safe boundary
            if kind == "runtime":
                self._runtime_status = "DEGRADED"
            self._fail("Runtime boot failed" if kind == "runtime" else "Conversation failed",
                       f"{type(exc).__name__}: request could not complete.")
            return
        if kind == "runtime":
            self._live_health = dict(reply)
            self._runtime_status = "ONLINE"
            self._record("system", "Frozen runtime composition is online; EventBus attached.")
            self._emit("runtime_started", correlation_id, {"services": len(self._live_health)})
            self.changed.emit()
            return
        status = getattr(reply, "status", "completed")
        text = str(getattr(reply, "text", reply))
        proposal_id = getattr(reply, "proposal_id", None)
        self._record("jarvis", text)
        if status == "waiting_for_approval" and proposal_id:
            proposal = self._chat.pending_proposal
            if proposal is not None and proposal.proposal_id == proposal_id:
                self._pending = {
                    "proposal_id": proposal.proposal_id,
                    "session_id": proposal.session_id,
                    "scope": proposal.scope,
                    "operation": proposal.capability,
                    "target": proposal.target,
                    "expires_at": proposal.expires_at,
                    "status": "WAITING_FOR_APPROVAL",
                }
                self._core_state, self._mission_stage = "WAITING_FOR_APPROVAL", 3
                self._emit("approval_required", correlation_id, {"proposal_id": proposal_id})
            else:
                self._fail("Approval unavailable", "The authoritative proposal was no longer live.")
                return
        elif status in {"error", "rejected"}:
            self._core_state = "ERROR"
            self._error = text
            self._emit("error", correlation_id, {"status": status})
        elif status == "cancelled":
            self._core_state, self._mission_stage = "IDLE", 0
            self._emit("cancelled", correlation_id, {})
        else:
            if kind == "approval" and self._pending:
                self._resolved.add(str(self._pending["proposal_id"]))
                self._pending = None
                self._emit("approval_resolved", correlation_id, {"status": status})
            self._core_state, self._mission_stage = "COMPLETED", 6
            self._emit("jarvis_response", correlation_id, {"status": status})
        self.changed.emit()

    def _apply_runtime_event(self, event: object) -> None:
        if self._closed or getattr(event, "session_id", None) != self._chat.auth_manager.session_id:
            return
        event_type = getattr(event, "event_type", "")
        agent_id = getattr(event, "agent_id", None)
        workflow_id = getattr(event, "workflow_id", None)
        if workflow_id in self._terminal_workflows:
            return
        if event_type == "workflow.started":
            self._core_state, self._mission_stage = "EXECUTING", 4
        elif event_type == "workflow.paused":
            self._core_state, self._mission_stage = "WAITING_FOR_APPROVAL", 3
        elif event_type == "workflow.completed":
            self._core_state, self._mission_stage = "COMPLETED", 6
            if workflow_id:
                self._terminal_workflows.add(workflow_id)
        elif event_type == "workflow.failed":
            self._core_state = "ERROR"
            self._error = "Workflow failed according to frozen runtime evidence."
            if workflow_id:
                self._terminal_workflows.add(workflow_id)
        elif agent_id:
            if event_type == "agent.started":
                self._agents[agent_id] = "ACTIVE"
            elif event_type == "agent.completed":
                self._agents[agent_id] = "COMPLETED"
            elif event_type == "agent.failed":
                self._agents[agent_id] = "FAILED"
        self._emit(event_type, f"runtime-{getattr(event, 'sequence', 0)}",
                    {"workflow_id": workflow_id, "agent_id": agent_id})
        self.changed.emit()

    def _record(self, role: str, text: str) -> None:
        self._messages.append({"role": role.upper(), "text": text[:4096], "timestamp": time.strftime("%H:%M:%S")})

    def _emit(self, event_type: str, correlation_id: str, payload: dict[str, Any]) -> None:
        event = self._events.normalize(event_type, session_id=self._chat.auth_manager.session_id,
                                       correlation_id=correlation_id, payload=payload)
        self._events.offer(event)

    def _fail(self, title: str, detail: str) -> None:
        self._core_state, self._mission_stage = "ERROR", 0
        self._error = f"{title}: {detail}"
        self._record("system", self._error)
        self.changed.emit()
