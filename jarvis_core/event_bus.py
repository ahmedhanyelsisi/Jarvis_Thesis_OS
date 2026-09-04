from typing import Callable, Any, Dict, List
import threading

class EventBus:
    """Foundation for decoupled event-driven architecture."""
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, handler: Callable) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, data: Any = None) -> None:
        with self._lock:
            handlers = self._subscribers.get(event_type, []).copy()
        
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error in event handler for {event_type}: {e}")
