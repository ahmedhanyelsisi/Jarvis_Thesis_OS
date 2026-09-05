from typing import Dict, Any, Optional
from .models import ThesisLifecycleState, PipelineState
from .chapter_manager import ChapterManager
from .approval_gate import ApprovalGate
from .revision_engine import RevisionEngine
from .citation_manager import CitationManager
from .exceptions import StateTransitionError

class PipelineManager:
    """Master orchestrator for the end-to-end thesis lifecycle."""
    
    # Allowed transitions mapping
    TRANSITIONS = {
        ThesisLifecycleState.INIT: [ThesisLifecycleState.PLANNING],
        ThesisLifecycleState.PLANNING: [ThesisLifecycleState.PAUSED_FOR_APPROVAL],
        ThesisLifecycleState.PAUSED_FOR_APPROVAL: [ThesisLifecycleState.RESEARCHING, ThesisLifecycleState.ASSEMBLING],
        ThesisLifecycleState.RESEARCHING: [ThesisLifecycleState.DRAFTING],
        ThesisLifecycleState.DRAFTING: [ThesisLifecycleState.REVIEWING],
        ThesisLifecycleState.REVIEWING: [ThesisLifecycleState.REVISING, ThesisLifecycleState.PAUSED_FOR_APPROVAL],
        ThesisLifecycleState.REVISING: [ThesisLifecycleState.DRAFTING],
        ThesisLifecycleState.ASSEMBLING: [ThesisLifecycleState.PAUSED_FOR_APPROVAL, ThesisLifecycleState.PUBLISHED]
    }
    
    def __init__(self, session_id: str, event_bus=None, file_access=None):
        self._session_id = session_id
        self._state = ThesisLifecycleState.INIT
        self._event_bus = event_bus
        
        self.chapters = ChapterManager()
        self.approvals = ApprovalGate()
        self.revision = RevisionEngine(self.chapters)
        self.citations = CitationManager(file_access)

    def get_state(self) -> PipelineState:
        return PipelineState(
            session_id=self._session_id,
            current_state=self._state,
            chapters=self.chapters.get_all_statuses(),
            dependencies=self.chapters.get_all_dependencies()
        )

    def advance_state(self, new_state: ThesisLifecycleState):
        """Advances the master thesis state."""
        allowed = self.TRANSITIONS.get(self._state, [])
        if new_state not in allowed:
            raise StateTransitionError(f"Cannot transition from {self._state.name} to {new_state.name}")
            
        # Cannot advance if pending approvals
        if self.approvals.has_pending():
            raise StateTransitionError("Cannot advance state while human approvals are pending.")
            
        self._state = new_state
        if self._event_bus:
            self._event_bus.publish("pipeline_state_changed", {"new_state": new_state.name})

    def request_human_approval(self, target_state: str, context: str) -> str:
        """Pauses the pipeline and issues an approval request."""
        # Force pipeline into paused state
        self._state = ThesisLifecycleState.PAUSED_FOR_APPROVAL
        req = self.approvals.create_request(target_state, context)
        return req.secure_token

    def submit_human_approval(self, request_id: str, token: str, approve: bool):
        """Processes the human approval response."""
        if approve:
            self.approvals.process_approval(request_id, token)
            # Find what the target was (mocking it for simplicity as advancing out of pause)
            # In real system, we'd pull req.target_state and advance.
        else:
            # Handle rejection
            pass
