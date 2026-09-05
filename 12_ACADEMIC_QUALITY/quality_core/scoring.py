from typing import Dict, List, Any
from .models import Metric, QualityScore
from .metrics import MetricDefinitions, validate_metric_score

class QualityScorer:
    """Calculates overall scores combining baseline, adaptive weighting, and objective alignment."""
    
    @staticmethod
    def calculate_score(raw_scores: Dict[str, float], reasonings: Dict[str, str], domain_context: Dict[str, Any]) -> QualityScore:
        weights = MetricDefinitions.get_adaptive_weights(domain_context)
        
        metrics = []
        overall = 0.0
        
        for name, weight in weights.items():
            raw = raw_scores.get(name, 0.0)
            validate_metric_score(raw)
            reasoning = reasonings.get(name, "No reasoning provided.")
            
            metric = Metric(name=name, score=raw, weight=weight, reasoning=reasoning)
            metrics.append(metric)
            
            overall += raw * weight
            
        # Ensure overall is capped to 10.0 due to floating point inaccuracies
        overall = min(max(overall, 0.0), 10.0)
        
        return QualityScore(
            overall_score=round(overall, 2),
            metrics=tuple(metrics)
        )
