"""Normalize known frozen-runtime EventBus topics for the HUD."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


KNOWN_TOPICS = frozenset(
    {
        "workflow.started", "workflow.paused", "workflow.completed", "workflow.failed",
        "agent.started", "agent.completed", "agent.failed",
    }
)

AGENT_ID_MAP = {
    "planneragent": "planner",
    "writeragent": "writer",
    "revieweragent": "reviewer",
    "builderagent": "builder",
    "researchagent": "research",
    "citationagent": "citation",
    "latexagent": "latex",
}


@dataclass(frozen=True)
class RuntimePresentationEvent:
    event_type: str
    sequence: int
    timestamp: float
    session_id: str
    workflow_id: str | None
    agent_id: str | None
    provenance: str
    payload: dict[str, Any]


class RuntimeEventAdapter:
    """Accept only subscribed frozen topics and strictly shaped payloads."""

    def __init__(self, session_id: str, deliver) -> None:
        self._session_id = session_id
        self._deliver = deliver
        self._sequence = 0
        self._active = True

    def close(self) -> None:
        self._active = False

    def handler_for(self, topic: str):
        def handler(payload: Any) -> None:
            self.accept(topic, payload)
        return handler

    def accept(self, topic: str, payload: Any) -> bool:
        if not self._active or topic not in KNOWN_TOPICS or not isinstance(payload, dict):
            return False
        workflow_id = payload.get("workflow_id")
        task_id = payload.get("task_id")
        agent_id = payload.get("agent_id")
        if workflow_id is not None and (not isinstance(workflow_id, str) or len(workflow_id) > 256):
            return False
        if task_id is not None and (not isinstance(task_id, str) or len(task_id) > 256):
            return False
        if agent_id is not None and (not isinstance(agent_id, str) or len(agent_id) > 128):
            return False
        # The frozen workflow topic provides task_id only. It cannot truthfully
        # identify a stone, so it remains an un-attributed workflow event.
        stone_id = AGENT_ID_MAP.get(agent_id.lower()) if agent_id else None
        self._sequence += 1
        self._deliver(RuntimePresentationEvent(
            event_type=topic, sequence=self._sequence, timestamp=time.time(),
            session_id=self._session_id, workflow_id=workflow_id,
            agent_id=stone_id, provenance="frozen_runtime_event_bus",
            payload={"task_id": task_id} if task_id else {},
        ))
        return True
