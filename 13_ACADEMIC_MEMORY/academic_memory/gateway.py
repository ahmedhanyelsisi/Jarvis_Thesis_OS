from typing import Dict, Any, Optional
from .memory_store import MemoryStore
from .feedback import FeedbackEngine
from .analytics import AnalyticsEngine
from .profile import ProfileManager
from .models import LearningPattern, ResearcherProfile, WorkflowOutcome

class AcademicMemoryGateway:
    """Safe exposure of Stone 22 to the Agent Cohort and Event Bus."""
    
    def __init__(self, workspace_root: str, session_id: str):
        self._session_id = session_id
        self._store = MemoryStore(workspace_root)
        self._feedback = FeedbackEngine(self._store)
        self._analytics = AnalyticsEngine(self._store)
        self._profile = ProfileManager(self._store)

    # --- AgentContext Exposed Methods ---
    
    def retrieve_memory(self, query: str) -> str:
        """Generic memory fetch for agents."""
        # Simple simulated retrieval based on topic
        pattern = self._feedback.get_learning_pattern(self._session_id, query)
        if pattern.confidence > 0.0:
            return f"Memory[{query}]: {pattern.pattern_description}"
        return f"No active memory for {query}."

    def store_feedback(self, context: str, text: str) -> str:
        """Agent/Human feedback entry point."""
        record = self._feedback.store_feedback(self._session_id, context, text)
        return record.feedback_id

    def get_learning_pattern(self, topic: str) -> LearningPattern:
        """Structured learning pattern fetch."""
        return self._feedback.get_learning_pattern(self._session_id, topic)

    def get_researcher_profile(self) -> ResearcherProfile:
        """Structured profile fetch."""
        # Typically session_id Maps to a specific researcher in a real multi-tenant setup.
        return self._profile.get_profile(self._session_id)
        
    # --- EventBus Subscriptions ---
    
    def handle_workflow_event(self, event_type: str, payload: Dict[str, Any]):
        """Passively ingests workflow telemetry."""
        if event_type == "workflow_completed":
            outcome = WorkflowOutcome(
                workflow_id=payload.get("workflow_id", "unknown"),
                status=payload.get("status", "completed"),
                steps_completed=payload.get("steps", 0),
                human_interventions=payload.get("interventions", 0)
            )
            self._analytics.log_workflow_outcome(outcome)
