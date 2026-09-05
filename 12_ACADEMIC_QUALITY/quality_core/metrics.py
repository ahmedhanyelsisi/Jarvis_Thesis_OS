from typing import Dict, Any, List
from .models import Metric
from .exceptions import MetricValidationError

class MetricDefinitions:
    BASELINE_METRICS = {
        "structure": 1.0,
        "argument": 1.0,
        "methodology": 1.0,
        "literature": 1.0,
        "citation": 1.0,
        "clarity": 1.0
    }
    
    @classmethod
    def get_adaptive_weights(cls, domain_context: Dict[str, Any]) -> Dict[str, float]:
        """Adjust baseline weights based on thesis domain context."""
        weights = dict(cls.BASELINE_METRICS)
        domain = domain_context.get("domain", "").lower()
        
        if "science" in domain or "engineering" in domain:
            weights["methodology"] = 1.5
            weights["citation"] = 1.2
        elif "humanities" in domain or "arts" in domain:
            weights["argument"] = 1.5
            weights["literature"] = 1.5
            
        # Normalize weights so they sum to 1.0
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

def validate_metric_score(score: float) -> None:
    if not (0.0 <= score <= 10.0):
        raise MetricValidationError(f"Score {score} is out of bounds [0.0, 10.0]")
