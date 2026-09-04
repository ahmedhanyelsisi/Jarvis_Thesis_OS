import time
from typing import Optional

from jarvis_core.interfaces import IEventBus
from latex_engine.compiler import LatexCompiler
from latex_engine.exceptions import CompilationTimeoutError, LatexEngineError

from .models import BuildTask, TaskStatus, BuildHistoryEntry
from .queue import BuildQueue

class BuildOrchestrator:
    """Thin controller managing BuildQueue state and LatexEngine execution without background threads."""
    
    def __init__(self, compiler: LatexCompiler, event_bus: IEventBus):
        self._compiler = compiler
        self._event_bus = event_bus
        self._queue = BuildQueue()
        
    def _safe_publish(self, event_name: str, payload: dict) -> None:
        """Publishes events safely, guaranteeing Orchestrator doesn't crash on telemetry failures."""
        try:
            self._event_bus.publish(event_name, payload)
        except Exception:
            pass
            
    def submit(self, request, priority: int = 10) -> str:
        """Constructs an immutable task, enqueues it, and emits the submitted event."""
        task = BuildTask(
            priority=priority,
            created_at=time.time(),
            request=request
        )
        self._queue.enqueue(task)
        self._safe_publish("build.submitted", {"task_id": task.task_id})
        return task.task_id
        
    def process_next(self) -> Optional[BuildTask]:
        """Dequeues the next task, executes it synchronously, and returns the strictly updated immutable state."""
        task = self._queue.dequeue()
        if not task:
            return None
            
        try:
            # Transition state by replacing the immutable object
            running_task = task.transition_to(TaskStatus.RUNNING)
        except Exception as e:
            # If transition fails, the task was likely invalidly injected. We abort without trying to execute.
            return task
            
        self._safe_publish("build.started", {"task_id": running_task.task_id})
        
        try:
            result = self._compiler.compile(running_task.request)
            
            status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            completed_task = running_task.transition_to(
                status,
                result=result,
                completed_at=time.time()
            )
            event_name = "build.completed" if result.success else "build.failed"
            self._safe_publish(event_name, {"task_id": completed_task.task_id})
            return completed_task
            
        except CompilationTimeoutError as e:
            failed_task = running_task.transition_to(
                TaskStatus.FAILED,
                error_message=str(e),
                completed_at=time.time()
            )
            self._safe_publish("build.failed", {"task_id": failed_task.task_id, "reason": "timeout"})
            return failed_task
            
        except Exception as e:
            failed_task = running_task.transition_to(
                TaskStatus.FAILED,
                error_message=f"System error: {str(e)}",
                completed_at=time.time()
            )
            self._safe_publish("build.failed", {"task_id": failed_task.task_id, "reason": "error"})
            return failed_task

    def to_history(self, task: BuildTask) -> BuildHistoryEntry:
        """Converts a final BuildTask into an immutable history footprint."""
        if not task.completed_at:
            raise ValueError("Cannot convert incomplete task to history")
            
        duration = task.completed_at - task.created_at
        return BuildHistoryEntry(
            task_id=task.task_id,
            status=task.status,
            duration_seconds=duration,
            completed_at=task.completed_at,
            success=(task.status == TaskStatus.COMPLETED),
            error_message=task.error_message
        )
