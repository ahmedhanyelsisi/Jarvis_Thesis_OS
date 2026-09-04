"""Small synchronous event bus for internal cognitive UI communication."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from threading import RLock
from typing import Any

from .dashboard_models import UIEvent


COMMAND_RECEIVED = "command_received"
WORKFLOW_STARTED = "workflow_started"
AGENT_STARTED = "agent_started"
AGENT_COMPLETED = "agent_completed"
MEMORY_UPDATED = "memory_updated"
RESPONSE_READY = "response_ready"

UI_EVENT_TYPES = frozenset(
    {
        COMMAND_RECEIVED,
        WORKFLOW_STARTED,
        AGENT_STARTED,
        AGENT_COMPLETED,
        MEMORY_UPDATED,
        RESPONSE_READY,
    }
)

EventHandler = Callable[[UIEvent], None]


class EventBus:
    """Publish UI events to subscribers while retaining a session history."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[UIEvent] = []
        self._lock = RLock()

    @property
    def history(self) -> tuple[UIEvent, ...]:
        """Return an immutable snapshot of emitted events."""

        with self._lock:
            return tuple(self._history)

    def get_history(self, event_type: str | None = None) -> tuple[UIEvent, ...]:
        """Retrieve an immutable event-history snapshot, optionally filtered."""

        events = self.history
        if event_type is None:
            return events
        return tuple(event for event in events if event.event_type == event_type)

    retrieve_event_history = get_history

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type or ``*`` for every event."""

        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(
        self,
        event: UIEvent | str,
        data: dict[str, Any] | None = None,
        *,
        source: str = "cognitive_ui",
        metadata: dict[str, Any] | None = None,
    ) -> UIEvent:
        """Record and synchronously deliver an event."""

        ui_event = event if isinstance(event, UIEvent) else UIEvent(
            event,
            data or {},
            source=source,
            metadata=metadata or {},
        )
        with self._lock:
            self._history.append(ui_event)
            handlers = tuple(
                self._subscribers.get(ui_event.event_type, ())
            ) + tuple(self._subscribers.get("*", ()))
        for handler in handlers:
            handler(ui_event)
        return ui_event

    publish = emit

    def clear(self) -> None:
        """Clear retained history without changing subscriptions."""

        with self._lock:
            self._history.clear()
