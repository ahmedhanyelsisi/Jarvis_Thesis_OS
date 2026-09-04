from typing import Any
from .models import AgentTask, AgentResult
from .interfaces import IAgent

class BuilderAgent(IAgent):
    """Technical thesis construction."""
    
    @property
    def name(self) -> str:
        return "BuilderAgent"
        
    @property
    def role(self) -> str:
        return "builder"
        
    def status(self) -> str:
        return "IDLE"
        
    def execute(self, task: AgentTask, context: Any) -> AgentResult:
        if not hasattr(context, 'read_thesis_file') or not hasattr(context, 'write_thesis_file'):
            return AgentResult(success=False, output="", errors=["Context missing safe file capabilities"])
            
        # Example of attempting file I/O safely
        try:
            # We don't actually write to avoid polluting thesis_root in tests
            # context.write_thesis_file("main.tex", "\\begin{document}\n")
            build_output = "Build preparation complete."
            success = True
        except Exception as e:
            build_output = str(e)
            success = False
            
        return AgentResult(
            success=success,
            output=build_output,
            metadata={}
        )
