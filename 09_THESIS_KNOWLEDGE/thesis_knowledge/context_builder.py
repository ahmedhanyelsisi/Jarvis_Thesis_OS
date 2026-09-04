from typing import List
import re

from .models import SemanticResult, ASTNode, ContextPackage

class ContextBuilder:
    """Combines chunks, sanitizes input, and builds academic context packages."""
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize text to prevent prompt injection and malformed LaTeX."""
        if not isinstance(text, str):
            return ""
        # Remove null bytes
        sanitized = text.replace("\x00", "")
        # Prevent massive unclosed LaTeX braces attacks
        if sanitized.count("{") > 100 or sanitized.count("}") > 100:
            # simple mitigation, just clip it if it's clearly an attack
            sanitized = sanitized[:1000] + "\n... [CONTENT TRUNCATED DUE TO COMPLEXITY] ..."
        return sanitized.strip()

    def build_context(self, goal: str, results: List[SemanticResult], ast_nodes: List[ASTNode]) -> ContextPackage:
        """Create an immutable context package for agents."""
        sanitized_goal = self.sanitize(goal)
        
        # Build sanitized text representation
        text_parts = []
        for res in results:
            clean_content = self.sanitize(res.content)
            text_parts.append(f"[{res.file_path}] (relevance: {res.distance:.2f})\n{clean_content}")
            
        full_text = "\n\n---\n\n".join(text_parts)
        
        return ContextPackage(
            goal=sanitized_goal,
            structured_ast=tuple(ast_nodes),
            semantic_results=tuple(results),
            sanitized_text=full_text
        )
