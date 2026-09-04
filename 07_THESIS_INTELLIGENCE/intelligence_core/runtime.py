from typing import Any, Dict, Optional

from .interfaces import IAgent
from .context import AgentContext
from .gateways import LLMGateway, MemoryGateway
from .exceptions import AgentNotFoundError, AgentRuntimeError

class AgentRuntimeManager:
    """
    Manages the lifecycle of IAgent instances.
    Acts as the secure intermediary between IntelligenceOrchestrator and agents.
    Ensures every agent is sandboxed through AgentContext and errors are isolated.
    """
    
    def __init__(self, build_orchestrator, llm_gateway: LLMGateway, memory_gateway: MemoryGateway):
        self._build_orchestrator = build_orchestrator
        self._llm_gateway = llm_gateway
        self._memory_gateway = memory_gateway
        self._agents: Dict[str, IAgent] = {}
        
    def register_agent(self, agent: IAgent) -> None:
        """Register an IAgent by its role. Does not allow duplicate roles."""
        if agent.role in self._agents:
            raise AgentRuntimeError(f"Agent role '{agent.role}' is already registered.")
        self._agents[agent.role] = agent
        
    def dispatch_event(self, event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast an OS event to all agents. Errors per agent are isolated, never propagated."""
        results = {}
        for role, agent in self._agents.items():
            try:
                result = agent.handle_event(event_name, payload)
                results[role] = result
            except Exception as e:
                results[role] = {"error": f"Agent runtime error: {str(e)}"}
        return results
        
    def route_message(self, target_role: str, sender_role: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route a message from one agent to another through the secure runtime boundary."""
        if target_role not in self._agents:
            raise AgentNotFoundError(f"No agent registered with role '{target_role}'")
        try:
            return self._agents[target_role].handle_message(sender_role, payload)
        except Exception as e:
            raise AgentRuntimeError(f"Agent '{target_role}' crashed handling message: {str(e)}") from e
            
    def build_context(self, agent_role: str) -> AgentContext:
        """Construct the restricted AgentContext sandbox for a specific agent."""
        return AgentContext(
            agent_role=agent_role,
            build_orchestrator=self._build_orchestrator,
            llm_gateway=self._llm_gateway,
            memory_gateway=self._memory_gateway,
            message_router=lambda target, payload: self.route_message(target, agent_role, payload)
        )
        
    def list_agents(self) -> Dict[str, str]:
        """Return registered agent roles and their class names."""
        return {role: type(agent).__name__ for role, agent in self._agents.items()}
