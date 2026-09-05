from .models import AgentPerformance, WorkflowOutcome
from .memory_store import MemoryStore

class AnalyticsEngine:
    """Tracks and analyzes Agent and Workflow metrics over time."""
    
    def __init__(self, store: MemoryStore):
        self._store = store

    def log_agent_performance(self, perf: AgentPerformance):
        # In a real system, we'd fetch existing, compute moving average, etc.
        # For Stone 22 architectural bounds, we just store it securely.
        self._store.upsert_agent_performance(perf)

    def log_workflow_outcome(self, outcome: WorkflowOutcome):
        self._store.insert_workflow_outcome(outcome)
