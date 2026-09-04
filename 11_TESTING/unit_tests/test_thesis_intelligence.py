import pytest
from pathlib import Path
from unittest.mock import MagicMock
from typing import Dict, Any, Optional

from intelligence_core import (
    LLMGateway, MemoryGateway,
    AgentRuntimeManager, IntelligenceOrchestrator, AgentContext,
    LLMGatewayError, MemoryGatewayError,
    AgentNotFoundError, AgentRuntimeError
)

# ---------------------------------------------------------------------------
# Minimal stub agent satisfying the IAgent protocol
# ---------------------------------------------------------------------------

class StubAgent:
    def __init__(self, role: str):
        self._role = role
        self.events_received = []
        self.messages_received = []

    @property
    def role(self) -> str:
        return self._role

    def handle_event(self, event_name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.events_received.append((event_name, payload))
        return {"handled": True, "event": event_name}

    def handle_message(self, sender_role: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.messages_received.append((sender_role, payload))
        return {"replied": True}

class CrashingAgent:
    @property
    def role(self) -> str:
        return "crasher"

    def handle_event(self, event_name: str, payload: Dict[str, Any]):
        raise RuntimeError("Agent intentionally crashed!")

    def handle_message(self, sender_role: str, payload: Dict[str, Any]):
        raise RuntimeError("Message handler crashed!")

# ---------------------------------------------------------------------------
# LLMGateway Tests
# ---------------------------------------------------------------------------

def test_llm_gateway_stub_mode():
    gw = LLMGateway(provider=None)
    result = gw.complete("Hello world")
    assert "LLM_STUB" in result

def test_llm_gateway_provider_called():
    mock_provider = MagicMock()
    mock_provider.complete.return_value = "Deep thought"
    gw = LLMGateway(provider=mock_provider)
    result = gw.complete("What is 42?", context={"key": "val"})
    assert result == "Deep thought"
    mock_provider.complete.assert_called_once_with("What is 42?", {"key": "val"})

def test_llm_gateway_provider_failure():
    mock_provider = MagicMock()
    mock_provider.complete.side_effect = RuntimeError("Connection timeout")
    gw = LLMGateway(provider=mock_provider)
    with pytest.raises(LLMGatewayError, match="Connection timeout"):
        gw.complete("Question?")

# Stone 14A hardening — mandatory patch tests
def test_llm_gateway_provider_returns_none_gives_empty_string():
    """V1 hardening: provider returning None must be normalized to '' not passed to agents."""
    mock_provider = MagicMock()
    mock_provider.complete.return_value = None
    gw = LLMGateway(provider=mock_provider)
    result = gw.complete("any prompt")
    assert result == ""
    assert isinstance(result, str)

def test_llm_gateway_valid_string_unchanged():
    """Contract: valid str response from provider must pass through unmodified."""
    mock_provider = MagicMock()
    mock_provider.complete.return_value = "A valid response."
    gw = LLMGateway(provider=mock_provider)
    result = gw.complete("prompt")
    assert result == "A valid response."

def test_llm_gateway_provider_returns_none_timeout_still_raises():
    """Existing timeout/error handling must be unaffected by the None-guard."""
    mock_provider = MagicMock()
    mock_provider.complete.side_effect = TimeoutError("LLM timed out")
    gw = LLMGateway(provider=mock_provider)
    with pytest.raises(LLMGatewayError, match="LLM timed out"):
        gw.complete("prompt")

# ---------------------------------------------------------------------------
# MemoryGateway Tests
# ---------------------------------------------------------------------------

def test_memory_gateway_stub_mode():
    gw = MemoryGateway(knowledge_manager=None)
    results = gw.search("some query")
    assert results == []

def test_memory_gateway_search_called():
    mock_km = MagicMock()
    mock_km.search.return_value = [{"content": "doc1"}, {"content": "doc2"}]
    gw = MemoryGateway(knowledge_manager=mock_km)
    results = gw.search("thesis chapter", top_k=2)
    assert len(results) == 2
    assert results[0]["content"] == "doc1"
    mock_km.search.assert_called_once_with("thesis chapter", top_k=2)

def test_memory_gateway_search_failure():
    mock_km = MagicMock()
    mock_km.search.side_effect = Exception("DB locked")
    gw = MemoryGateway(knowledge_manager=mock_km)
    with pytest.raises(MemoryGatewayError, match="DB locked"):
        gw.search("query")

# ---------------------------------------------------------------------------
# AgentRuntimeManager Tests
# ---------------------------------------------------------------------------

def make_runtime():
    mock_orchestrator = MagicMock()
    llm = LLMGateway()
    mem = MemoryGateway()
    return AgentRuntimeManager(build_orchestrator=mock_orchestrator, llm_gateway=llm, memory_gateway=mem)

def test_runtime_registers_agent():
    rm = make_runtime()
    a = StubAgent("writer")
    rm.register_agent(a)
    assert "writer" in rm.list_agents()

def test_runtime_rejects_duplicate_role():
    rm = make_runtime()
    rm.register_agent(StubAgent("writer"))
    with pytest.raises(AgentRuntimeError, match="already registered"):
        rm.register_agent(StubAgent("writer"))

def test_runtime_dispatch_event():
    rm = make_runtime()
    a = StubAgent("writer")
    rm.register_agent(a)
    results = rm.dispatch_event("build.completed", {"task_id": "abc"})
    assert "writer" in results
    assert results["writer"]["handled"] is True
    assert len(a.events_received) == 1

def test_runtime_dispatch_event_isolates_crash():
    """A crashing agent must not propagate its failure to other agents."""
    rm = make_runtime()
    rm.register_agent(CrashingAgent())
    rm.register_agent(StubAgent("writer"))
    results = rm.dispatch_event("build.failed", {"task_id": "abc"})
    assert "error" in results["crasher"]
    assert results["writer"]["handled"] is True

def test_runtime_route_message():
    rm = make_runtime()
    rm.register_agent(StubAgent("writer"))
    rm.register_agent(StubAgent("reviewer"))
    result = rm.route_message("reviewer", "writer", {"content": "Review chapter 2"})
    assert result["replied"] is True

def test_runtime_route_message_not_found():
    rm = make_runtime()
    with pytest.raises(AgentNotFoundError, match="unknown_agent"):
        rm.route_message("unknown_agent", "writer", {})

def test_runtime_route_message_crash_propagated():
    rm = make_runtime()
    rm.register_agent(CrashingAgent())
    with pytest.raises(AgentRuntimeError, match="crashed"):
        rm.route_message("crasher", "writer", {})

# ---------------------------------------------------------------------------
# AgentContext Sandbox Tests
# ---------------------------------------------------------------------------

def test_context_submit_build():
    mock_orchestrator = MagicMock()
    mock_orchestrator.submit.return_value = "task-xyz"
    ctx = AgentContext(
        agent_role="writer",
        build_orchestrator=mock_orchestrator,
        llm_gateway=LLMGateway(),
        memory_gateway=MemoryGateway(),
        message_router=lambda t, p: None
    )
    tid = ctx.submit_build("D:/thesis", "main.tex", priority=1)
    assert tid == "task-xyz"

def test_context_query_memory():
    mock_km = MagicMock()
    mock_km.search.return_value = [{"content": "chapter1"}]
    ctx = AgentContext(
        agent_role="writer",
        build_orchestrator=MagicMock(),
        llm_gateway=LLMGateway(),
        memory_gateway=MemoryGateway(knowledge_manager=mock_km),
        message_router=lambda t, p: None
    )
    results = ctx.query_memory("latex errors", top_k=1)
    assert results[0]["content"] == "chapter1"

def test_context_message_routing():
    calls = []
    def router(target, payload):
        calls.append((target, payload))
        return {"ack": True}

    ctx = AgentContext(
        agent_role="writer",
        build_orchestrator=MagicMock(),
        llm_gateway=LLMGateway(),
        memory_gateway=MemoryGateway(),
        message_router=router
    )
    result = ctx.send_message("reviewer", {"content": "check this"})
    assert result["ack"] is True
    assert calls[0] == ("reviewer", {"content": "check this"})

# ---------------------------------------------------------------------------
# IntelligenceOrchestrator Tests
# ---------------------------------------------------------------------------

def test_orchestrator_activation_subscribes():
    mock_bus = MagicMock()
    mock_runtime = MagicMock()
    orch = IntelligenceOrchestrator(event_bus=mock_bus, agent_runtime=mock_runtime)
    orch.activate()
    assert mock_bus.subscribe.call_count == len(IntelligenceOrchestrator.FORWARDED_EVENTS)

def test_orchestrator_activation_idempotent():
    mock_bus = MagicMock()
    orch = IntelligenceOrchestrator(event_bus=mock_bus, agent_runtime=MagicMock())
    orch.activate()
    orch.activate()  # Second call must not add duplicate subscriptions
    assert mock_bus.subscribe.call_count == len(IntelligenceOrchestrator.FORWARDED_EVENTS)

def test_orchestrator_event_bus_failure_does_not_crash():
    mock_bus = MagicMock()
    mock_bus.publish.side_effect = Exception("Bus down")
    mock_runtime = MagicMock()
    mock_runtime.dispatch_event.return_value = {"writer": {"handled": True}}
    orch = IntelligenceOrchestrator(event_bus=mock_bus, agent_runtime=mock_runtime)
    # Simulate an OS event directly (should not crash despite EventBus being down)
    orch._on_os_event("build.completed", {"task_id": "123"})

# ---------------------------------------------------------------------------
# Architecture Boundary Scan
# ---------------------------------------------------------------------------

def test_forbidden_imports_intelligence_core():
    core_dir = Path("07_THESIS_INTELLIGENCE/intelligence_core")
    import ast
    forbidden = {"socket", "requests", "urllib", "aiohttp", "httpx", "asyncio", "multiprocessing"}
    
    for py_file in core_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, \
                        f"Forbidden import '{alias.name}' in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module.split(".")[0] not in forbidden, \
                        f"Forbidden import '{node.module}' in {py_file}"
