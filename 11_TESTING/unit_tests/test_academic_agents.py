import pytest
from unittest.mock import MagicMock
from pathlib import Path
import ast
import uuid

from academic_agents.models import AgentTask, AgentExecutionPolicy, AgentResult
from academic_agents.interfaces import IAgent
from academic_agents.planner import PlannerAgent
from academic_agents.writer import WriterAgent
from academic_agents.reviewer import ReviewerAgent
from academic_agents.builder import BuilderAgent
from academic_agents.orchestrator import AcademicAgentOrchestrator
from academic_agents.exceptions import PolicyViolationError

def test_all_agents_implement_iagent():
    agents = [PlannerAgent(), WriterAgent(), ReviewerAgent(), BuilderAgent()]
    for agent in agents:
        assert isinstance(agent, IAgent)
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'role')
        assert hasattr(agent, 'execute')
        assert hasattr(agent, 'status')

def test_planner_retrieves_context():
    planner = PlannerAgent()
    mock_ctx = MagicMock()
    mock_ctx.search_thesis.return_value = ["mock_chunk1", "mock_chunk2"]
    
    task = AgentTask(task_id="1", agent_name="PlannerAgent", objective="Write intro")
    result = planner.execute(task, mock_ctx)
    
    mock_ctx.search_thesis.assert_called_with("Write intro")
    assert result.success is True
    assert result.metadata["chunks_found"] == 2

def test_writer_receives_semantic_context():
    writer = WriterAgent()
    mock_ctx = MagicMock()
    mock_pkg = MagicMock()
    mock_pkg.goal = "Draft chapter 1"
    mock_pkg.sanitized_text = "Clean text"
    mock_ctx.build_context.return_value = mock_pkg
    
    task = AgentTask(task_id="1", agent_name="WriterAgent", objective="Draft chapter 1")
    result = writer.execute(task, mock_ctx)
    
    mock_ctx.build_context.assert_called_with("Draft chapter 1")
    assert result.success is True
    assert "Drafted content" in result.output

def test_reviewer_produces_review_output():
    reviewer = ReviewerAgent()
    mock_ctx = MagicMock()
    mock_ast = MagicMock()
    mock_ast.node_type = "chapter"
    mock_ctx.get_document_structure.return_value = mock_ast
    
    task = AgentTask(task_id="1", agent_name="ReviewerAgent", objective="Review ch1")
    result = reviewer.execute(task, mock_ctx)
    
    mock_ctx.get_document_structure.assert_called_with("thesis")
    assert result.success is True
    assert result.metadata["node_type"] == "chapter"

def test_builder_cannot_bypass_safe_file_access():
    builder = BuilderAgent()
    mock_ctx = MagicMock()
    # It must use context.read_thesis_file and write_thesis_file
    # Check that it checks for these capabilities
    mock_ctx.read_thesis_file = MagicMock()
    mock_ctx.write_thesis_file = MagicMock()
    
    task = AgentTask(task_id="1", agent_name="BuilderAgent", objective="Build")
    result = builder.execute(task, mock_ctx)
    assert result.success is True
    
    # If missing capabilities, should fail
    mock_fail_ctx = MagicMock(spec=[])
    res_fail = builder.execute(task, mock_fail_ctx)
    assert res_fail.success is False
    assert "missing safe file capabilities" in res_fail.errors[0]

def test_agent_execution_policy_stops_infinite_loops():
    # Simulate a timeout policy enforcement in the orchestrator
    mock_bus = MagicMock()
    mock_runtime = MagicMock()
    
    policy = AgentExecutionPolicy(timeout_seconds=0) # Instant timeout
    orchestrator = AcademicAgentOrchestrator(mock_bus, mock_runtime, policy)
    
    # Create a slow agent
    class SlowAgent(IAgent):
        @property
        def name(self): return "SlowAgent"
        @property
        def role(self): return "slow"
        def status(self): return "IDLE"
        def execute(self, task, ctx):
            import time
            time.sleep(0.1)
            return AgentResult(True, "")
            
    slow_agent = SlowAgent()
    orchestrator.register_agent(slow_agent)
    
    task = AgentTask(task_id="1", agent_name="SlowAgent", objective="Run")
    res = orchestrator.dispatch_task(task)
    
    assert res.success is False
    assert "exceeded timeout" in res.errors[0]

def test_legacy_agents_cannot_be_imported():
    pkg_dir = Path("10_ACADEMIC_AGENTS/academic_agents")
    forbidden = {"02_AI_AGENTS", "jarvis", "os"} # allowed OS in test, but not in agents
    
    for py_file in pkg_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    assert name not in forbidden, f"Forbidden import {alias.name} in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split(".")[0]
                    assert name not in forbidden, f"Forbidden import {node.module} in {py_file}"
