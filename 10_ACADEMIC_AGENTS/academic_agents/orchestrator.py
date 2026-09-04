import time
import uuid
from typing import Dict, Any, Optional

from jarvis_core.interfaces import IEventBus
from intelligence_core import AgentRuntimeManager
from .models import AgentTask, AgentResult, AgentExecutionPolicy
from .exceptions import PolicyViolationError, TaskExecutionError
from .interfaces import IAgent

class AcademicAgentOrchestrator:
    """Orchestrates Stone 17 agents, enforcing policy and routing tasks."""

    def __init__(self, event_bus: IEventBus, runtime: AgentRuntimeManager, policy: AgentExecutionPolicy = None):
        self._event_bus = event_bus
        self._runtime = runtime
        self._policy = policy or AgentExecutionPolicy()
        self._agents: Dict[str, IAgent] = {}

    def register_agent(self, agent: IAgent) -> None:
        self._agents[agent.name] = agent
        # Create a bridge to Stone 14's AgentRuntimeManager
        self._runtime.register_agent(AgentBridge(agent, self))

    def dispatch_task(self, task: AgentTask) -> AgentResult:
        """Route a task to an agent, enforcing execution policy."""
        if task.agent_name not in self._agents:
            return AgentResult(success=False, output="", errors=[f"Agent {task.agent_name} not found"])
            
        agent = self._agents[task.agent_name]
        
        # Build the Stone 14 sandbox context
        ctx = self._runtime.build_context(agent.role)
        
        start_time = time.time()
        
        try:
            # Policy enforcement: Timeout handled conceptually by wrapper logic
            # In a real async loop we'd use asyncio.wait_for, but this is sync.
            # We pass the policy down to the agent or enforce it post-execution.
            result = agent.execute(task, ctx)
            
            elapsed = time.time() - start_time
            if elapsed > self._policy.timeout_seconds:
                raise PolicyViolationError(f"Agent {agent.name} exceeded timeout of {self._policy.timeout_seconds}s")
                
            return result
        except PolicyViolationError as pve:
            return AgentResult(success=False, output="", errors=[str(pve)])
        except Exception as e:
            return AgentResult(success=False, output="", errors=[f"Execution failed: {e}"])

class AgentBridge:
    """Adapts Stone 17 IAgent to Stone 14 AgentRuntimeManager."""
    def __init__(self, agent: IAgent, orchestrator: AcademicAgentOrchestrator):
        self._agent = agent
        self._orchestrator = orchestrator
        
    @property
    def role(self) -> str:
        return self._agent.role
        
    def handle_event(self, event_name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            agent_name=self._agent.name,
            objective=f"Handle event {event_name}",
            context=payload
        )
        res = self._orchestrator.dispatch_task(task)
        return {"success": res.success, "output": res.output}

    def handle_message(self, sender_role: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            agent_name=self._agent.name,
            objective=f"Handle message from {sender_role}",
            context=payload
        )
        res = self._orchestrator.dispatch_task(task)
        return {"success": res.success, "output": res.output}
