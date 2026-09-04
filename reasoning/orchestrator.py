"""Dependency-aware sequential workflow execution."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from .models import PlannedTask, TaskStatus, WorkflowState


class WorkflowOrchestrator:
    """Execute planned work through the existing AgentManager interface."""

    def __init__(self, agent_manager: Any) -> None:
        self.agent_manager = agent_manager

    def execute(
        self,
        tasks: list[PlannedTask],
        workflow_id: str | None = None,
    ) -> WorkflowState:
        """Execute tasks in dependency order and return the final state."""

        self._validate_plan(tasks)
        state = WorkflowState(workflow_id=workflow_id or str(uuid4()))
        task_map = {task.id: task for task in tasks}

        while any(task.status == TaskStatus.PENDING for task in tasks):
            progressed = False
            for task in tasks:
                if task.status != TaskStatus.PENDING:
                    continue
                dependency_states = [task_map[item].status for item in task.dependencies]
                if any(status in (TaskStatus.FAILED, TaskStatus.SKIPPED) for status in dependency_states):
                    task.status = TaskStatus.SKIPPED
                    task.result = {"error": "A dependency did not complete successfully."}
                    state.skipped_tasks.append(task.id)
                    progressed = True
                    continue
                if not all(status == TaskStatus.COMPLETED for status in dependency_states):
                    continue
                self._execute_task(task, state)
                progressed = True

            if not progressed:
                for task in tasks:
                    if task.status == TaskStatus.PENDING:
                        task.status = TaskStatus.SKIPPED
                        task.result = {"error": "Unresolvable or cyclic dependencies."}
                        state.skipped_tasks.append(task.id)
                break

        state.current_task = None
        return state

    def run(
        self,
        tasks: list[PlannedTask],
        workflow_id: str | None = None,
    ) -> WorkflowState:
        """Alias for :meth:`execute` used by workflow-facing callers."""

        return self.execute(tasks, workflow_id)

    def _execute_task(self, task: PlannedTask, state: WorkflowState) -> None:
        state.current_task = task.id
        task.status = TaskStatus.RUNNING
        payload = self._task_payload(task, state.outputs)
        try:
            response = self.agent_manager.send_task(task.required_agent, payload)
            if isinstance(response, dict) and response.get("status") == "failed":
                task.status = TaskStatus.FAILED
                task.result = response
                state.failed_tasks.append(task.id)
                return
            task.status = TaskStatus.COMPLETED
            task.result = response
            state.completed_tasks.append(task.id)
            state.outputs[task.id] = response
        except Exception as error:  # Agent boundaries must not crash a workflow.
            task.status = TaskStatus.FAILED
            task.result = {"error": str(error), "exception": type(error).__name__}
            state.failed_tasks.append(task.id)

    @staticmethod
    def _task_payload(task: PlannedTask, outputs: dict[str, Any]) -> str:
        if not task.dependencies:
            return task.description
        context = {task_id: outputs[task_id] for task_id in task.dependencies if task_id in outputs}
        return f"{task.description}\nDependency outputs: {json.dumps(context, default=str, sort_keys=True)}"

    @staticmethod
    def _validate_plan(tasks: list[PlannedTask]) -> None:
        ids = [task.id for task in tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Task ids must be unique.")
        known = set(ids)
        missing = {item for task in tasks for item in task.dependencies if item not in known}
        if missing:
            raise ValueError(f"Unknown task dependencies: {sorted(missing)}")
