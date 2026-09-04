from typing import Any
from .models import AgentTask, AgentResult
from .interfaces import IAgent

class PlannerAgent(IAgent):
    """Converts thesis goals into structured execution plans."""
    
    @property
    def name(self) -> str:
        return "PlannerAgent"
        
    @property
    def role(self) -> str:
        return "planner"
        
    def status(self) -> str:
        return "IDLE"
        
    def execute(self, task: AgentTask, context: Any) -> AgentResult:
        """Analyze user objective and retrieve context to create tasks."""
        if not hasattr(context, 'search_thesis'):
            return AgentResult(success=False, output="", errors=["Context missing search_thesis capability"])
            
        # Retrieve relevant thesis context from Stone 16
        results = context.search_thesis(task.objective)
        
        # Create ordered tasks (simulated)
        plan = f"Plan created for objective: {task.objective}\nTasks:\n1. Draft section\n2. Review section"
        
        # In a full run, we would use context.complete_llm to build the plan
        # but here we ensure the architecture is sound.
        llm_prompt = f"Plan this: {task.objective} based on {len(results)} chunks."
        # result = context.complete_llm(llm_prompt)
        
        return AgentResult(
            success=True,
            output=plan,
            metadata={"chunks_found": len(results)}
        )
