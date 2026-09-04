from typing import Any, Dict

class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        
    def register(self, name: str, service: Any) -> None:
        if name in self._services:
            raise ValueError(f"Service '{name}' is already registered. Duplicate registrations are not allowed.")
        self._services[name] = service
        
    def get(self, name: str) -> Any:
        if name not in self._services:
            raise KeyError(f"Service '{name}' not found in registry")
        return self._services[name]

    def has(self, name: str) -> bool:
        return name in self._services

    def clear(self) -> None:
        self._services.clear()
