from typing import Protocol, Any, Callable

class IService(Protocol):
    pass

class IEventBus(Protocol):
    def publish(self, event_type: str, data: Any = None) -> None: ...
    def subscribe(self, event_type: str, handler: Callable) -> None: ...
