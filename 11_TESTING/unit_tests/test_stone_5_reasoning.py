"""Comprehensive tests for the Stone 5 reasoning and orchestration layer."""

from pathlib import Path

from reasoning import (
    AgentRouter,
    EvaluationLoop,
    PlannedTask,
    ReasoningEngine,
    ReasoningMemory,
    TaskPlanner,
    TaskStatus,
    WorkflowOrchestrator,
)


class RecordingAgentManager:
    """Small AgentManager-compatible test double."""

    def __init__(self, fail_agent=None):
        self.fail_agent = fail_agent
        self.calls = []
        self.agents = [
            "literature_agent",
            "thesis_writer_agent",
            "latex_agent",
            "diagram_agent",
            "reviewer_agent",
            "test_agent",
        ]

    def list_agents(self):
        return list(self.agents)

    def send_task(self, agent, task):
        self.calls.append((agent, task))
        if agent == self.fail_agent:
            return {"status": "failed", "message": "intentional failure"}
        return {
            "status": "completed",
            "agent": agent,
            "result": {"response": f"Completed detailed output for {task}"},
        }


def test_reasoning_engine_creates_deterministic_academic_plan():
    strategy = ReasoningEngine().analyze("Write methodology chapter for my thesis")

    assert strategy.task_type == "academic_writing"
    assert strategy.complexity == "complex"
    assert strategy.steps[0] == "Analyze research objectives"
    assert "literature_agent" in strategy.required_agents
    assert "latex_agent" in strategy.required_agents


def test_reasoning_engine_handles_simple_diagram_task():
    strategy = ReasoningEngine().analyze("Create architecture diagram")

    tasks = TaskPlanner(AgentRouter(RecordingAgentManager())).plan(strategy)

    assert strategy.task_type == "diagram_creation"
    assert strategy.required_agents[0] == "diagram_agent"
    assert tasks[0].required_agent == "diagram_agent"
    assert tasks[-1].required_agent == "reviewer_agent"


def test_planner_decomposes_and_orders_tasks():
    manager = RecordingAgentManager()
    strategy = ReasoningEngine().analyze("Write methodology chapter for my thesis")
    tasks = TaskPlanner(AgentRouter(manager)).create_plan(strategy)

    assert len(tasks) == len(strategy.steps)
    assert tasks[0].dependencies == []
    assert tasks[1].dependencies == [tasks[0].id]
    assert tasks[-1].required_agent == "reviewer_agent"
    assert all(task.status == TaskStatus.PENDING for task in tasks)


def test_router_selects_registered_agents_and_writer_alias():
    router = AgentRouter(RecordingAgentManager())

    assert router.route("Find papers about transformers") == "literature_agent"
    assert router.route("Create architecture diagram") == "diagram_agent"
    assert router.route("Draft the chapter", "writer_agent") == "thesis_writer_agent"


def test_workflow_executes_tasks_and_passes_dependency_outputs():
    manager = RecordingAgentManager()
    tasks = [
        PlannedTask("task-1", "Find papers", "literature_agent"),
        PlannedTask("task-2", "Write summary", "thesis_writer_agent", ["task-1"]),
    ]

    state = WorkflowOrchestrator(manager).execute(tasks, "workflow-test")

    assert state.workflow_id == "workflow-test"
    assert state.completed_tasks == ["task-1", "task-2"]
    assert state.failed_tasks == []
    assert "Dependency outputs" in manager.calls[1][1]
    assert tasks[1].status == TaskStatus.COMPLETED


def test_workflow_failure_skips_dependent_tasks():
    manager = RecordingAgentManager(fail_agent="literature_agent")
    tasks = [
        PlannedTask("task-1", "Find papers", "literature_agent"),
        PlannedTask("task-2", "Write summary", "thesis_writer_agent", ["task-1"]),
    ]

    state = WorkflowOrchestrator(manager).execute(tasks)

    assert state.failed_tasks == ["task-1"]
    assert state.skipped_tasks == ["task-2"]
    assert tasks[0].status == TaskStatus.FAILED
    assert tasks[1].status == TaskStatus.SKIPPED


def test_reasoning_memory_persists_history_and_preferences(tmp_path: Path):
    memory_path = tmp_path / "reasoning.json"
    memory = ReasoningMemory(memory_path)
    strategy = ReasoningEngine().analyze("Create architecture diagram")
    tasks = TaskPlanner(AgentRouter(RecordingAgentManager())).create_plan(strategy)
    state = WorkflowOrchestrator(RecordingAgentManager()).execute(tasks, "persisted-flow")

    memory.record_workflow(state, strategy)
    memory.set_preference("output_format", "LaTeX")
    restored = ReasoningMemory(memory_path)

    assert restored.recall()["previous_workflows"][0]["workflow_id"] == "persisted-flow"
    assert restored.recall()["successful_strategies"][0]["task_type"] == "diagram_creation"
    assert restored.get_preference("output_format") == "LaTeX"


def test_evaluation_generates_dimension_feedback():
    evaluation = EvaluationLoop().evaluate("")

    assert evaluation.score < 7
    assert evaluation.issues
    assert set(evaluation.dimensions) == {
        "completeness",
        "correctness",
        "consistency",
        "formatting",
    }
    assert evaluation.recommendation.startswith("Improve")


def test_evaluation_loop_requests_bounded_improvement():
    manager = RecordingAgentManager()
    result = EvaluationLoop(manager, quality_threshold=9).evaluate_and_improve(
        "short",
        "thesis_writer_agent",
        "Write a complete methodology",
        max_iterations=1,
    )

    assert result["improvement_attempts"] == 1
    assert len(result["evaluations"]) == 2
    assert any(agent == "reviewer_agent" for agent, _ in manager.calls)
    assert any(agent == "thesis_writer_agent" for agent, _ in manager.calls)
