import uuid
from typing import List, Tuple
from .models import Argument, Claim, ReasoningConfidence
from .confidence_engine import ConfidenceEngine

class ArgumentAnalyzer:
    """Analyzes text to extract and evaluate arguments."""
    
    def analyze(self, text: str, mapped_claims: List[Claim]) -> Argument:
        """Constructs an argument from claims and evaluates its strength."""
        
        confidence = ConfidenceEngine.calculate(tuple(mapped_claims))
        
        # Strength heuristic based on confidence and number of claims
        strength = min(10.0, confidence.score * 10.0 * (1.0 + 0.1 * len(mapped_claims)))
        
        conclusion = "Derived conclusion from claims." if mapped_claims else "Unsupported text."
        
        return Argument(
            argument_id=str(uuid.uuid4()),
            claims=tuple(mapped_claims),
            conclusion=conclusion,
            strength=strength,
            confidence=confidence
        )
