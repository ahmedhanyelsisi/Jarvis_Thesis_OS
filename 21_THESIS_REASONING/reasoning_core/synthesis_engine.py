from typing import List
from .models import ReasoningResult, Argument, Contradiction

class SynthesisEngine:
    """Merges all reasoning components into a final synthesized result."""
    
    @staticmethod
    def synthesize(arguments: List[Argument], contradictions: List[Contradiction]) -> ReasoningResult:
        summary = "Reasoning Synthesis Complete. "
        
        if contradictions:
            summary += f"Found {len(contradictions)} logical contradictions requiring resolution. "
        else:
            summary += "No logical contradictions detected. "
            
        strong_args = sum(1 for a in arguments if a.strength > 7.0)
        summary += f"{strong_args} out of {len(arguments)} arguments are strongly supported."
        
        return ReasoningResult(
            arguments=tuple(arguments),
            contradictions=tuple(contradictions),
            synthesis_summary=summary
        )
