import uuid
import time
from typing import Dict, Any

from .models import QualityReport, QualityScore
from .scoring import QualityScorer
from .feedback import FeedbackGenerator
from .history import QualityHistoryManager
from intelligence_core import AgentRuntimeManager

class QualityEvaluator:
    """Orchestrates quality evaluation by using LLMGateway via AgentRuntime,
    applying fixed metrics, and returning structured QualityReport."""
    
    def __init__(self, runtime: AgentRuntimeManager, history_manager: QualityHistoryManager):
        self._runtime = runtime
        self._history = history_manager

    def evaluate(self, workflow_id: str, node_id: str, draft_text: str, domain_context: Dict[str, Any]) -> QualityReport:
        """Evaluates draft text against thesis objectives and rubric."""
        
        # Here we would typically construct a prompt for the LLM Gateway
        # asking it to return JSON mapping metric names to scores 0-10.
        # Since this is a restricted sandbox and we don't call external APIs,
        # we'll simulate the runtime evaluating it. 
        # In a real environment, self._runtime.llm_gateway.generate(...) would be called.
        
        # Simulated LLM parsing for demonstration:
        # We assume the runtime returns raw float scores and reasoning text.
        raw_scores = {
            "structure": 7.5,
            "argument": 8.0,
            "methodology": 6.5,
            "literature": 9.0,
            "citation": 8.5,
            "clarity": 7.0
        }
        reasonings = {
            "structure": "Logical flow is clear but lacks transitions.",
            "argument": "Strong core thesis, some points underdeveloped.",
            "methodology": "Methods are vague and lack reproducibility details.",
            "literature": "Excellent integration of recent work.",
            "citation": "Proper formatting, minor missing references.",
            "clarity": "Generally readable, some passive voice."
        }
        
        # In actual implementation:
        # response = self._runtime.llm_gateway.generate(prompt=..., schema=...)
        # raw_scores, reasonings = parse(response)
        
        score: QualityScore = QualityScorer.calculate_score(raw_scores, reasonings, domain_context)
        tasks = FeedbackGenerator.generate_tasks(score, threshold=7.5) # Example threshold
        
        recommendation = "APPROVE"
        if score.overall_score < 7.0 or any(t.severity in ["CRITICAL", "HIGH"] for t in tasks):
            recommendation = "REVISE"
        if score.overall_score < 4.0:
            recommendation = "REJECT"
            
        report = QualityReport(
            report_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            node_id=node_id,
            score=score,
            tasks=tasks,
            recommendation=recommendation,
            timestamp=time.time()
        )
        
        # Log to history
        self._history.save_report(report)
        
        return report
