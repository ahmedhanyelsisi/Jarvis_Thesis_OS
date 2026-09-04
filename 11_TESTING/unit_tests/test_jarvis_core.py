import pytest
from jarvis_core.registry import ServiceRegistry
from jarvis_core.event_bus import EventBus

def test_service_registry():
    registry = ServiceRegistry()
    registry.register("test_service", "hello")
    assert registry.has("test_service")
    assert registry.get("test_service") == "hello"

    with pytest.raises(KeyError):
        registry.get("non_existent")

def test_service_registry_prevents_duplicates():
    registry = ServiceRegistry()
    registry.register("test_service", "hello")
    with pytest.raises(ValueError, match="is already registered"):
        registry.register("test_service", "world")

def test_event_bus():
    bus = EventBus()
    received = []
    def handler(data):
        received.append(data)
        
    bus.subscribe("test_event", handler)
    bus.publish("test_event", "hello")
    
    assert len(received) == 1
    assert received[0] == "hello"

def test_bootstrap_failure_diagnostics():
    from jarvis_core.bootstrap import bootstrap_system, BootstrapError
    # Provide a configuration that triggers an exception during bootstrap
    # For example, invalid memory_config type that causes get() to fail
    with pytest.raises(BootstrapError, match="Failed to bootstrap"):
        bootstrap_system(config={"memory": "invalid_type"})

def test_event_bus_error_handling():
    bus = EventBus()
    received = []
    
    def bad_handler(data):
        raise ValueError("Oops")
        
    def good_handler(data):
        received.append(data)
        
    bus.subscribe("test_event", bad_handler)
    bus.subscribe("test_event", good_handler)
    
    # Should not raise exception to the caller
    bus.publish("test_event", "hello")
    
    assert len(received) == 1
    assert received[0] == "hello"
