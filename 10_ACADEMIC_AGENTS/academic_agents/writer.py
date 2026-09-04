from typing import Any
from .models import AgentTask, AgentResult
from .interfaces import IAgent

class WriterAgent(IAgent):
    """Generates academic content."""
    
    @property
    def name(self) -> str:
        return "WriterAgent"
        
    @property
    def role(self) -> str:
        return "writer"
        
    def status(self) -> str:
        return "IDLE"
        
    def execute(self, task: AgentTask, context: Any) -> AgentResult:
        if not hasattr(context, 'build_context'):
            return AgentResult(success=False, output="", errors=["Context missing build_context capability"])
            
        # Retrieve semantic context
        ctx_pkg = context.build_context(task.objective)
        
        # simulated generation
        draft = f"Drafted content based on sanitized context of length {len(ctx_pkg.sanitized_text)}."
        
        return AgentResult(
            success=True,
            output=draft,
            metadata={"goal": ctx_pkg.goal}
        )
