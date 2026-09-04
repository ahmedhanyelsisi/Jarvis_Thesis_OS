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
from build_orchestration.exceptions import InvalidStateTransitionError

def test_hardened_task_mutations():
    """Verify malicious or accidental mutations are aggressively blocked."""
    task = BuildTask(priority=1, created_at=time.time(), request=BuildRequest(target_dir=Path(".")))
    
    # 1. Attribute modification should fail
    with pytest.raises(FrozenInstanceError):
        task.status = TaskStatus.COMPLETED
        
    # 2. History entry modification should fail
    entry = BuildHistoryEntry(
        task_id="test",
        status=TaskStatus.COMPLETED,
        duration_seconds=1.0,
        completed_at=time.time(),
        success=True
    )
    with pytest.raises(FrozenInstanceError):
        entry.success = False

def test_hardened_invalid_transitions():
    """Verify transitions must follow PENDING -> RUNNING -> COMPLETED/FAILED."""
    task = BuildTask(priority=1, created_at=time.time(), request=BuildRequest(target_dir=Path(".")))
    
    # Valid: PENDING -> RUNNING
    t_run = task.transition_to(TaskStatus.RUNNING)
    assert t_run.status == TaskStatus.RUNNING
    
    # Invalid: PENDING -> COMPLETED
    with pytest.raises(InvalidStateTransitionError):
        task.transition_to(TaskStatus.COMPLETED)
        
    # Invalid: COMPLETED -> RUNNING (Going backwards)
    t_comp = t_run.transition_to(TaskStatus.COMPLETED)
    with pytest.raises(InvalidStateTransitionError):
        t_comp.transition_to(TaskStatus.RUNNING)

def test_hardened_event_bus_failure():
    """Ensure Orchestrator does NOT crash if telemetry/event_bus fails."""
    mock_compiler = MagicMock()
    mock_compiler.compile.return_value = BuildResult(success=True, duration_seconds=1.0, diagnostics=(), artifacts=())
    
    # Hostile event bus that crashes on every publish
    mock_event_bus = MagicMock()
    mock_event_bus.publish.side_effect = Exception("Telemetry network down!")
    
    orchestrator = BuildOrchestrator(compiler=mock_compiler, event_bus=mock_event_bus)
    
    # Submit should not crash
    task_id = orchestrator.submit(BuildRequest(target_dir=Path(".")), priority=5)
    
    # Process should not crash, and should still return a COMPLETED task
    task = orchestrator.process_next()
    assert task is not None
    assert task.task_id == task_id
    assert task.status == TaskStatus.COMPLETED

def test_hardened_invalid_task_injection():
    """Verify if a completed task is manually injected into queue, orchestrator aborts cleanly."""
    mock_compiler = MagicMock()
    mock_event_bus = MagicMock()
    orchestrator = BuildOrchestrator(compiler=mock_compiler, event_bus=mock_event_bus)
    
    # Malicious injection of a COMPLETED task
    task = BuildTask(priority=1, created_at=time.time(), request=BuildRequest(target_dir=Path(".")))
    t_run = task.transition_to(TaskStatus.RUNNING)
    t_comp = t_run.transition_to(TaskStatus.COMPLETED)
    
    orchestrator._queue.enqueue(t_comp)
    
    # Orchestrator should abort transitioning COMPLETED -> RUNNING, and just return the task
    processed_task = orchestrator.process_next()
    assert processed_task.status == TaskStatus.COMPLETED
    # Ensure compile was never called
    mock_compiler.compile.assert_not_called()

def test_hardened_queue_integrity():
    """Verify queue strictly orders without executing."""
    q = BuildQueue()
    req = BuildRequest(target_dir=Path("."))
    
    # Duplicate priority test
    t1 = BuildTask(priority=5, created_at=2.0, request=req)
    t2 = BuildTask(priority=5, created_at=1.0, request=req)
    t3 = BuildTask(priority=1, created_at=3.0, request=req)
    
    q.enqueue(t1)
    q.enqueue(t2)
    q.enqueue(t1) # Duplicate task reference is allowed, ordered by created_at which is same
    q.enqueue(t3)
    
    assert q.dequeue() == t3 # Priority 1
    assert q.dequeue() == t2 # Priority 5, created earliest
    assert q.dequeue() == t1 # Priority 5, created later
    assert q.dequeue() == t1 # Duplicate reference
    
def test_hardened_forbidden_imports():
    """Verify that build_orchestration strictly respects hostile scan boundaries."""
    engine_dir = Path("06_BUILD_ORCHESTRATION/build_orchestration")
    import ast
    
    forbidden = {"socket", "requests", "urllib", "aiohttp", "httpx", "jarvis_agents", "memory", "voice", "UI", "threading", "asyncio", "multiprocessing"}
    
    for py_file in engine_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # 'threading' is allowed only in queue.py for Lock, but we can verify it doesn't spin threads
                    if alias.name == "threading" and py_file.name != "queue.py":
                        pytest.fail(f"Threading imported in {py_file}")
                    elif alias.name != "threading":
                        assert alias.name.split(".")[0] not in forbidden, f"Forbidden import {alias.name} in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module.split(".")[0] not in forbidden, f"Forbidden import {node.module} in {py_file}"
