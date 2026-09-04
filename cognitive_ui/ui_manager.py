"""Top-level controller for text, voice, and future visual UI adapters."""

from __future__ import annotations

from typing import Any

from .command_center import CommandCenter, JarvisKernel
from .event_bus import EventBus
from .session_state import SessionState
from .dashboard_metrics import DashboardMetrics
from .session_store import SessionStore


class UIManager:
    """Coordinate UI commands and status without implementing reasoning."""

    def __init__(
        self,
        jarvis: JarvisKernel,
        *,
        session_state: SessionState | None = None,
        event_bus: EventBus | None = None,
        session_store: SessionStore | None = None,
        metrics: DashboardMetrics | None = None,
    ) -> None:
        self.command_center = CommandCenter(
            jarvis,
            session_state=session_state,
            event_bus=event_bus,
            session_store=session_store,
            metrics=metrics,
        )

    @property
    def session_state(self) -> SessionState:
        return self.command_center.session_state

    @property
    def event_bus(self) -> EventBus:
        return self.command_center.event_bus

    def handle_command(
        self,
        command: str,
        *,
        workflow: bool = False,
        evaluate: bool = True,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        return self.command_center.send_command(
            command,
            workflow=workflow,
            evaluate=evaluate,
            confirmed=confirmed,
        )

    process_command = handle_command

    def get_dashboard(self) -> dict[str, Any]:
        """Return a transport-neutral snapshot for any future renderer."""

        return {
            "session": self.session_state.snapshot(),
            "system_status": self.command_center.get_system_status(),
            "events": [event.to_dict() for event in self.event_bus.history],
            "metrics": self.command_center.get_metrics(),
        }
