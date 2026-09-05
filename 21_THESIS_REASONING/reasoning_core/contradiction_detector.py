from typing import List, Tuple
from .models import Claim, Contradiction

class ContradictionDetector:
    """Identifies logical clashes between claims."""
    
    @staticmethod
    def detect(claims: List[Claim]) -> List[Contradiction]:
        contradictions = []
        
        # Simple heuristic for demonstration of capability.
        # A real system leverages LLM logic to detect semantic contradictions.
        for i, claim_a in enumerate(claims):
            for claim_b in claims[i+1:]:
                # Toy example: "A is true" vs "A is false"
                text_a = claim_a.text.lower()
                text_b = claim_b.text.lower()
                
                # Basic negation check
                if text_a == f"not {text_b}" or text_b == f"not {text_a}" or text_a == f"{text_b} is false" or text_b == f"{text_a} is false":
                    contradictions.append(Contradiction(
                        description="Direct logical negation detected between claims.",
                        conflicting_claims=(claim_a, claim_b),
                        severity="CRITICAL"
                    ))
                    
        return contradictions
