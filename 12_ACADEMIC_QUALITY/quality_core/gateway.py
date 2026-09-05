from typing import Dict, Any, Optional
from .evaluator import QualityEvaluator
from workflow.orchestrator import WorkflowOrchestrator
from workflow.models import WorkflowState, WorkflowNode

class QualityGate:
    """Provides non-blocking quality evaluation integration for workflows.
    Stone 18 Orchestrator queries this gate to enrich nodes with quality data,
    but retains full control over routing."""

    def __init__(self, evaluator: QualityEvaluator, workflow_orchestrator: WorkflowOrchestrator):
        self._evaluator = evaluator
        self._workflow = workflow_orchestrator

    def evaluate_node_output(self, workflow_id: str, node_id: str, output_text: str, context: Dict[str, Any]) -> None:
        """Evaluates output and updates the workflow state indirectly (e.g. by enriching context or events).
        The orchestrator decides what to do with the report (retry, human checkpoint, proceed)."""
        report = self._evaluator.evaluate(
            workflow_id=workflow_id,
            node_id=node_id,
            draft_text=output_text,
            domain_context=context
        )
        
        # Publish event for UI and Orchestrator observation
        self._workflow._event_bus.publish("quality.evaluation.completed", {
            "workflow_id": workflow_id,
            "node_id": node_id,
            "report_id": report.report_id,
            "score": report.score.overall_score,
            "recommendation": report.recommendation
        })
        
        # In a real system, the workflow engine might pause here if recommendation == "REJECT"
        # Since Stone 19 is non-blocking natively, we leave that DAG routing rule to Stone 18.
