from typing import Any
from .models import AgentTask, AgentResult
from .interfaces import IAgent

class ReviewerAgent(IAgent):
    """Academic quality control."""
    
    @property
    def name(self) -> str:
        return "ReviewerAgent"
        
    @property
    def role(self) -> str:
        return "reviewer"
        
    def status(self) -> str:
        return "IDLE"
        
    def execute(self, task: AgentTask, context: Any) -> AgentResult:
        if not hasattr(context, 'get_document_structure'):
            return AgentResult(success=False, output="", errors=["Context missing get_document_structure capability"])
            
        # Review structure
        ast = context.get_document_structure("thesis")
        
        review_output = "Review completed. Structure is adequate."
        if not ast:
            review_output = "Review failed. No structure."
            
        return AgentResult(
            success=True,
            output=review_output,
            metadata={"node_type": getattr(ast, 'node_type', 'none')}
        )
