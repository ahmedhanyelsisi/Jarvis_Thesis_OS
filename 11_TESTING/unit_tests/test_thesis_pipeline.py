import pytest
from pipeline_core.exceptions import ApprovalError, RevisionLimitError, StateTransitionError, ChapterDependencyError
from pipeline_core.pipeline_manager import PipelineManager
from pipeline_core.models import ThesisLifecycleState, ChapterState
from pipeline_core.chapter_manager import ChapterManager
from pipeline_core.revision_engine import RevisionEngine

def test_fake_approval_injection():
    pipeline = PipelineManager("session_1")
    pipeline.request_human_approval("TARGET", "context")
    # In reality, request_id is returned or mapped. 
    # For the test, we'll fetch the only pending request.
    req_id = list(pipeline.approvals._pending_requests.keys())[0]
    
    with pytest.raises(ApprovalError, match="Invalid secure token"):
        pipeline.submit_human_approval(req_id, "fake_token", True)

def test_infinite_revision_loops():
    cm = ChapterManager()
    cm.register_chapter("ch1")
    engine = RevisionEngine(cm)
    
    engine.request_revision("ch1")
    engine.request_revision("ch1")
    with pytest.raises(RevisionLimitError, match="reached max revisions"):
        engine.request_revision("ch1")

def test_unauthorized_state_transitions():
    pipeline = PipelineManager("session_1")
    with pytest.raises(StateTransitionError):
        pipeline.advance_state(ThesisLifecycleState.PUBLISHED)

def test_chapter_dependency_corruption():
    cm = ChapterManager()
    cm.register_chapter("ch1")
    cm.register_chapter("ch2", depends_on=["ch1"])
    
    # Try to draft ch2 before ch1 is APPROVED
    with pytest.raises(ChapterDependencyError, match="is not APPROVED"):
        cm.update_state("ch2", ChapterState.DRAFTING)

def test_agent_bypass_attempts():
    pipeline = PipelineManager("session_1")
    # Agent requests human approval
    token = pipeline.request_human_approval("TARGET", "context")
    # Pipeline is now paused.
    assert pipeline.get_state().current_state == ThesisLifecycleState.PAUSED_FOR_APPROVAL
    
    # Try to advance without finishing approval
    with pytest.raises(StateTransitionError, match="human approvals are pending"):
        pipeline.advance_state(ThesisLifecycleState.RESEARCHING)
