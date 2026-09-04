from typing import Any
from .models import ASTNode

class CopilotBridge:
    """Restricted adapter for Stone 11 AcademicCopilot and Stone 10 Workspace."""
    
    def __init__(self, academic_copilot: Any):
        self._copilot = academic_copilot
        
    def get_structure(self, target: str) -> ASTNode:
        """Fetch structure from thesis context (Stone 11)."""
        try:
            # We fetch the context and map it to our immutable ASTNode
            ctx = self._copilot.thesis_context()
            
            # Find the chapter or return the whole thing
            # For simplicity, returning a high-level view
            return ASTNode(
                node_type="thesis",
                title="Thesis Structure",
                content=None,
                children=tuple(
                    ASTNode(
                        node_type="chapter",
                        title=f.split("/")[-1],
                        content=None
                    )
                    for f in ctx.chapters
                )
            )
        except Exception as e:
            return ASTNode(node_type="error", title="Error fetching structure", content=str(e))
