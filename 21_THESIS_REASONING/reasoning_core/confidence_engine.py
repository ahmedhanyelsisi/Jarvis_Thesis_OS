from typing import Tuple
from .models import Claim, ReasoningConfidence

class ConfidenceEngine:
    """Calculates confidence scores based on evidence density and source quality."""
    
    @staticmethod
    def calculate(claims: Tuple[Claim, ...]) -> ReasoningConfidence:
        if not claims:
            return ReasoningConfidence(0.0, ("No claims provided",))
            
        total_evidence = sum(len(c.evidence) for c in claims)
        
        score = min(1.0, total_evidence * 0.25)
        factors = [f"Found {total_evidence} supporting pieces of evidence."]
        
        if score < 0.5:
            factors.append("Low evidence density. Argument requires more citations.")
        elif score >= 0.75:
            factors.append("Strong evidence density.")
            
        return ReasoningConfidence(
            score=score,
            factors=tuple(factors)
        )
