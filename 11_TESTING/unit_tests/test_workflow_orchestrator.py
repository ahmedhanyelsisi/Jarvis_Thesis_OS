import pytest
from unittest.mock import MagicMock
from pathlib import Path
import json

from workflow.models import WorkflowState, WorkflowNode, Checkpoint
from workflow.persistence import WorkflowPersistence
from workflow.checkpoints import CheckpointType
from workflow.scheduler import WorkflowScheduler
from workflow.orchestrator import WorkflowOrchestrator
from workflow.exceptions import InfiniteLoopError

@pytest.fixture
def temp_workspace(tmp_path):
    # Simulate a workspace with .jarvis/workflows
    return str(tmp_path)

@pytest.fixture
def mock_agent_orch():
    orch = MagicMock()
    # By default, mock agent success
    orch.dispatch_task.return_value = MagicMock(success=True, output="Done", metadata={}, errors=[])
    return orch

@pytest.fixture
def workflow_orch(temp_workspace, mock_agent_orch):
    bus = MagicMock()
    persistence = WorkflowPersistence(temp_workspace)
    return WorkflowOrchestrator(bus, mock_agent_orch, persistence)

def test_workflow_creation_and_persistence(workflow_orch, temp_workspace):
    nodes = {
        "1": WorkflowNode(node_id="1", agent_type="PlannerAgent", input={}),
        "2": WorkflowNode(node_id="2", agent_type="WriterAgent", input={})
    }
    state = workflow_orch.create_workflow("test_wf", "thesis_improvement", nodes)
    
    # Check persistence
    pers = WorkflowPersistence(temp_workspace)
    loaded = pers.load("test_wf")
    assert loaded is not None
    assert loaded.workflow_id == "test_wf"
    assert loaded.status == "PENDING"
    assert len(loaded.nodes) == 2

def test_workflow_execution_sequence(workflow_orch):
    nodes = {
        "1": WorkflowNode(node_id="1", agent_type="PlannerAgent", input={})
    }
    state = workflow_orch.create_workflow("test_seq", "thesis_improvement", nodes)
    
    # First step runs node 1
    state = workflow_orch.step("test_seq")
    assert state.status == "RUNNING"
    assert "1" in state.completed_nodes
    assert state.nodes["1"].status == "COMPLETED"

    # Next step should complete the workflow
    state = workflow_orch.step("test_seq")
    assert state.status == "COMPLETED"

def test_human_checkpoint_pause_and_resume(workflow_orch):
    nodes = {"1": WorkflowNode(node_id="1", agent_type="WriterAgent", input={})}
    state = workflow_orch.create_workflow("test_hitl", "thesis_improvement", nodes)
    
    # Request checkpoint
    state = workflow_orch.request_checkpoint(state, CheckpointType.B_WRITE_DISK, "1")
    assert state.status == "PAUSED"
    assert state.pending_checkpoint is not None
    
    # Step should do nothing because it's paused
    state2 = workflow_orch.step("test_hitl")
    assert state2.status == "PAUSED"
    
    # Resolve checkpoint
    state = workflow_orch.resolve_checkpoint("test_hitl", state.pending_checkpoint.checkpoint_id, approved=True)
    assert state.status == "RUNNING"
    assert state.pending_checkpoint is None

def test_agent_retry_and_failure(workflow_orch, mock_agent_orch):
    nodes = {"1": WorkflowNode(node_id="1", agent_type="WriterAgent", input={}, max_retries=2)}
    workflow_orch.create_workflow("test_fail", "thesis", nodes)
    
    # Mock failure
    mock_agent_orch.dispatch_task.return_value = MagicMock(success=False, output="", metadata={}, errors=["Error"])
    
    # Step 1: fails, retry 1
    state = workflow_orch.step("test_fail")
    assert state.nodes["1"].status == "PENDING"
    assert state.nodes["1"].retry_count == 1
    
    # Step 2: fails, hits max retries (2) -> status FAILED
    state = workflow_orch.step("test_fail")
    assert state.nodes["1"].status == "FAILED"
    assert state.status == "FAILED"

def test_infinite_loop_protection(temp_workspace, mock_agent_orch):
    bus = MagicMock()
    persistence = WorkflowPersistence(temp_workspace)
    scheduler = WorkflowScheduler(max_steps=3)
    orch = WorkflowOrchestrator(bus, mock_agent_orch, persistence, scheduler)
    
    nodes = {"1": WorkflowNode(node_id="1", agent_type="WriterAgent", input={})}
    state = orch.create_workflow("test_loop", "thesis", nodes)
    
    # Manually pad history to exceed limits
    state = orch._update_state(state, history=("step", "step", "step", "step"))
    
    state = orch.step("test_loop")
    assert state.status == "FAILED"
    assert "FAIL: Workflow test_loop exceeded 3 steps." in state.history[-1]

def test_workflow_isolation(workflow_orch, temp_workspace):
    nodes = {}
    workflow_orch.create_workflow("wf_A", "t1", nodes)
    workflow_orch.create_workflow("wf_B", "t2", nodes)
    
    pers = WorkflowPersistence(temp_workspace)
    assert pers.load("wf_A").workflow_id == "wf_A"
    assert pers.load("wf_B").workflow_id == "wf_B"

from workflow.exceptions import WorkflowPersistenceError

def test_workflow_id_path_traversal_blocked(workflow_orch, temp_workspace):
    nodes = {}
    bad_ids = ["../session", "../../jarvis/session", "C:\\windows\\system32", "test\x00byte"]
    
    for bad_id in bad_ids:
        with pytest.raises(WorkflowPersistenceError) as excinfo:
            workflow_orch.create_workflow(bad_id, "thesis", nodes)
        assert "Invalid workflow ID" in str(excinfo.value) or "Path resolution error" in str(excinfo.value)

def test_valid_workflow_id_still_persists(workflow_orch, temp_workspace):
    nodes = {}
    valid_id = "thesis_improvement_v1-2_uuid8932"
    workflow_orch.create_workflow(valid_id, "thesis", nodes)
    
    pers = WorkflowPersistence(temp_workspace)
    assert pers.load(valid_id) is not None

def test_corrupted_state_recovery(temp_workspace):
    pers = WorkflowPersistence(temp_workspace)
    
    # Manually create a corrupted json file
    bad_id = "corrupted_wf"
    file_path = Path(temp_workspace) / ".jarvis" / "workflows" / f"workflow_{bad_id}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("{ this is not valid json }", encoding="utf-8")
    
    with pytest.raises(WorkflowPersistenceError) as excinfo:
        pers.load(bad_id)
    assert "Corrupted workflow state JSON" in str(excinfo.value)
