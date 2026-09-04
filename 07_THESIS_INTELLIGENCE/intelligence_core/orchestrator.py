from typing import Any, Dict, Optional

from jarvis_core.interfaces import IEventBus
from .runtime import AgentRuntimeManager
from .gateways import LLMGateway, MemoryGateway
from .exceptions import IntelligenceLayerError

class IntelligenceOrchestrator:
    """
    Top-level coordinator of the Thesis Intelligence Layer.
    Bridges the EventBus (Stone 12.5), BuildOrchestrator (Stone 13B) and agents.
    Does NOT execute agents directly. Delegates to AgentRuntimeManager.
    Does NOT access memory or LLM directly. Delegates to gateways.
    Does NOT modify jarvis.py or any frozen stone.
    """
    
    FORWARDED_EVENTS = {"build.completed", "build.failed"}
    
    def __init__(
        self,
        event_bus: IEventBus,
        agent_runtime: AgentRuntimeManager
    ):
        self._event_bus = event_bus
        self._agent_runtime = agent_runtime
        self._subscribed = False
        
    def activate(self) -> None:
        """Subscribe to OS events. Must be called after bootstrap is complete."""
        if self._subscribed:
            return
        for event_name in self.FORWARDED_EVENTS:
            self._event_bus.subscribe(
                event_name,
                lambda data, en=event_name: self._on_os_event(en, data)
            )
        self._subscribed = True
        
    def _on_os_event(self, event_name: str, payload: Any) -> None:
        """Safely forward OS lifecycle events to all registered agents."""
        try:
            results = self._agent_runtime.dispatch_event(event_name, payload or {})
            self._event_bus.publish("intelligence.event.dispatched", {
                "event": event_name,
                "results": results
            })
        except Exception as e:
            self._safe_publish("intelligence.agent.error", {
                "event": event_name,
                "error": str(e)
            })
            
    def _safe_publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Publish telemetry without crashing if EventBus is degraded."""
        try:
            self._event_bus.publish(event_name, payload)
        except Exception:
            pass
