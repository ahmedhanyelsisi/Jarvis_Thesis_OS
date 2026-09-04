import pytest
import time
from unittest.mock import MagicMock
from pathlib import Path
from dataclasses import FrozenInstanceError

from latex_engine.models import BuildRequest, BuildResult
from latex_engine.exceptions import CompilationTimeoutError

from build_orchestration import (
    BuildTask,
    TaskStatus,
    BuildQueue,
    BuildOrchestrator,
    BuildHistoryEntry
)

def test_build_task_immutability():
    task = BuildTask(priority=1, created_at=time.time(), request=BuildRequest(target_dir=Path(".")))
    
    with pytest.raises(FrozenInstanceError):
        task.status = TaskStatus.COMPLETED
        
def test_build_queue_ordering():
    queue = BuildQueue()
    
    req = BuildRequest(target_dir=Path("."))
    
    # Priority 1 is "higher priority" than Priority 10 in standard integer sort
    t1 = BuildTask(priority=10, created_at=2.0, request=req)
    t2 = BuildTask(priority=1, created_at=1.0, request=req)
    t3 = BuildTask(priority=10, created_at=1.0, request=req)
    
    queue.enqueue(t1)
    queue.enqueue(t2)
    queue.enqueue(t3)
    
    # Expected order:
    # 1. t2 (priority=1)
    # 2. t3 (priority=10, earlier created_at)
    # 3. t1 (priority=10, later created_at)
    
    assert queue.dequeue() == t2
    assert queue.dequeue() == t3
    assert queue.dequeue() == t1
    assert queue.is_empty()

def test_orchestrator_success_flow():
    mock_compiler = MagicMock()
    mock_result = BuildResult(success=True, duration_seconds=1.5, diagnostics=(), artifacts=())
    mock_compiler.compile.return_value = mock_result
    
    mock_event_bus = MagicMock()
    
    orchestrator = BuildOrchestrator(compiler=mock_compiler, event_bus=mock_event_bus)
    
    req = BuildRequest(target_dir=Path("."))
    task_id = orchestrator.submit(req, priority=5)
    
    # Check submitted event
    mock_event_bus.publish.assert_any_call("build.submitted", {"task_id": task_id})
    
    # Process
    completed_task = orchestrator.process_next()
    
    assert completed_task is not None
    assert completed_task.task_id == task_id
    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.result == mock_result
    assert completed_task.completed_at is not None
    
    # Check other events
    mock_event_bus.publish.assert_any_call("build.started", {"task_id": task_id})
    mock_event_bus.publish.assert_any_call("build.completed", {"task_id": task_id})
    
    # Test history conversion
    history = orchestrator.to_history(completed_task)
    assert isinstance(history, BuildHistoryEntry)
    assert history.success is True
    assert history.task_id == task_id
    assert history.duration_seconds > 0

def test_orchestrator_failure_flow():
    mock_compiler = MagicMock()
    # Compilation failure (success=False but didn't crash)
    mock_result = BuildResult(success=False, duration_seconds=0.5, diagnostics=(), artifacts=())
    mock_compiler.compile.return_value = mock_result
    
    mock_event_bus = MagicMock()
    orchestrator = BuildOrchestrator(compiler=mock_compiler, event_bus=mock_event_bus)
    
    task_id = orchestrator.submit(BuildRequest(target_dir=Path(".")), priority=5)
    failed_task = orchestrator.process_next()
    
    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.result == mock_result
    mock_event_bus.publish.assert_any_call("build.failed", {"task_id": task_id})

def test_orchestrator_timeout_flow():
    mock_compiler = MagicMock()
    mock_compiler.compile.side_effect = CompilationTimeoutError("Timed out")
    
    mock_event_bus = MagicMock()
    orchestrator = BuildOrchestrator(compiler=mock_compiler, event_bus=mock_event_bus)
    
    task_id = orchestrator.submit(BuildRequest(target_dir=Path(".")), priority=5)
    failed_task = orchestrator.process_next()
    
    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.error_message == "Timed out"
    mock_event_bus.publish.assert_any_call("build.failed", {"task_id": task_id, "reason": "timeout"})

def test_orchestrator_system_error_flow():
    mock_compiler = MagicMock()
    mock_compiler.compile.side_effect = RuntimeError("Disk full")
    
    mock_event_bus = MagicMock()
    orchestrator = BuildOrchestrator(compiler=mock_compiler, event_bus=mock_event_bus)
    
    task_id = orchestrator.submit(BuildRequest(target_dir=Path(".")), priority=5)
    failed_task = orchestrator.process_next()
    
    assert failed_task.status == TaskStatus.FAILED
    assert "Disk full" in failed_task.error_message
    mock_event_bus.publish.assert_any_call("build.failed", {"task_id": task_id, "reason": "error"})

def test_forbidden_imports():
    """Verify that build_orchestration strictly respects boundaries."""
    engine_dir = Path("06_BUILD_ORCHESTRATION/build_orchestration")
    import ast
    
    forbidden = {"socket", "requests", "urllib", "aiohttp", "httpx", "jarvis_agents", "memory", "voice", "UI"}
    
    for py_file in engine_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, f"Forbidden import {alias.name} in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module.split(".")[0] not in forbidden, f"Forbidden import {node.module} in {py_file}"
