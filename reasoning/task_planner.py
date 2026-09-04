"""Task decomposition and dependency construction."""

from __future__ import annotations

from .agent_router import AgentRouter
from .models import ExecutionStrategy, PlannedTask


class TaskPlanner:
    """Convert a reasoning strategy into ordered executable tasks."""

    def __init__(self, router: AgentRouter | None = None) -> None:
        self.router = router or AgentRouter()

    def create_plan(self, strategy: ExecutionStrategy) -> list[PlannedTask]:
        """Build a sequential dependency graph from *strategy*.

        Dependencies are explicit, so a later executor can schedule independent
        tasks in parallel without changing the plan model.
        """

        tasks: list[PlannedTask] = []
        previous_id: str | None = None
        for index, description in enumerate(strategy.steps, start=1):
            preferred = self._preferred_agent(description, strategy.required_agents)
            task_id = f"task-{index}"
            tasks.append(
                PlannedTask(
                    id=task_id,
                    description=description,
                    required_agent=self.router.route(description, preferred),
                    dependencies=[previous_id] if previous_id else [],
                )
            )
            previous_id = task_id
        return tasks

    def decompose(self, strategy: ExecutionStrategy) -> list[PlannedTask]:
        """Backward-friendly alias for :meth:`create_plan`."""

        return self.create_plan(strategy)

    def plan(self, strategy: ExecutionStrategy) -> list[PlannedTask]:
        """Concise alias for :meth:`create_plan`."""

        return self.create_plan(strategy)

    @staticmethod
    def _preferred_agent(description: str, available: list[str]) -> str | None:
        text = description.lower()
        matches = (
            ("review", "reviewer_agent"),
            ("literature", "literature_agent"),
            ("latex", "latex_agent"),
            ("diagram", "diagram_agent"),
            ("test", "test_agent"),
            ("", "thesis_writer_agent"),
        )
        for keyword, agent in matches:
            if keyword in text and agent in available:
                return agent
        return None
