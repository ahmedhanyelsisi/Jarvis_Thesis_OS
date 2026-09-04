from typing import Any, Dict, List, Optional
from pathlib import Path

from .interfaces import IAgent
from .gateways import LLMGateway, MemoryGateway
from .exceptions import AgentNotFoundError, AgentRuntimeError

class AgentContext:
    """
    The restricted OS sandbox injected into every agent.
    Agents are forbidden from bypassing this — they must call all OS 
    services through these methods only.
    """
    
    def __init__(
        self,
        agent_role: str,
        build_orchestrator,
        llm_gateway: LLMGateway,
        memory_gateway: MemoryGateway,
        message_router  # Callable[str, dict] -> Optional[dict]
    ):
        self._agent_role = agent_role
        self._build_orchestrator = build_orchestrator
        self._llm = llm_gateway
        self._memory = memory_gateway
        self._router = message_router
        
    def submit_build(self, target_dir: str, main_file: str = "main.tex", priority: int = 10) -> str:
        """Request a LaTeX compilation through the Build Orchestrator."""
        from latex_engine.models import BuildRequest
        req = BuildRequest(target_dir=Path(target_dir), main_file=main_file)
        return self._build_orchestrator.submit(req, priority=priority)
        
    def query_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query the knowledge store through the MemoryGateway."""
        return self._memory.search(query, top_k=top_k)
        
    def complete_llm(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Submit a prompt to the LLM through the LLMGateway."""
        return self._llm.complete(prompt, context)
        
    def send_message(self, target_role: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route a message to another agent through the IntelligenceOrchestrator."""
        return self._router(target_role, payload)
