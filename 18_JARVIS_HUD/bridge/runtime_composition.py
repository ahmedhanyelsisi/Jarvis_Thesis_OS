"""Lifecycle adapter for the frozen Stone 24 runtime composition."""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Any

from .runtime_event_adapter import KNOWN_TOPICS, RuntimeEventAdapter


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "15_JARVIS_RUNTIME"


class LiveRuntimeComposition:
    """Boot once, subscribe through the frozen EventBus, then detach safely."""

    def __init__(self, *, session_id: str, deliver_event) -> None:
        self._session_id = session_id
        self._deliver_event = deliver_event
        self._lock = threading.RLock()
        self._started = False
        self._closed = False
        self._bootloader: Any | None = None
        self._adapter: RuntimeEventAdapter | None = None
        self._health: dict[str, str] = {}

    def start(self) -> dict[str, str]:
        with self._lock:
            if self._closed:
                raise RuntimeError("Runtime composition is closed")
            if self._started:
                return dict(self._health)
            if str(RUNTIME_ROOT) not in sys.path:
                sys.path.insert(0, str(RUNTIME_ROOT))
            from runtime_core.bootloader import JarvisBootloader

            bootloader = JarvisBootloader(str(ROOT))
            bootloader.boot()
            components = bootloader.get_runtime_components()
            registry = components["registry"]
            event_bus = registry.get("event_bus")
            if event_bus is None or not hasattr(event_bus, "subscribe"):
                raise RuntimeError("Frozen runtime EventBus is unavailable")
            adapter = RuntimeEventAdapter(self._session_id, self._deliver_event)
            for topic in KNOWN_TOPICS:
                event_bus.subscribe(topic, adapter.handler_for(topic))
            self._health = components["health_monitor"].perform_health_check()
            self._bootloader, self._adapter, self._started = bootloader, adapter, True
            return dict(self._health)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            if self._adapter is not None:
                # Frozen EventBus has no unsubscribe API. Disable this adapter so
                # retained handlers cannot alter a closed HUD.
                self._adapter.close()
            self._adapter = None
