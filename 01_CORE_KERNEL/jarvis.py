import sys
import os
import json
from pathlib import Path

import yaml


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


AI_AGENTS_PATH = os.path.join(
    PROJECT_ROOT,
    "02_AI_AGENTS"
)


sys.path.insert(
    0,
    AI_AGENTS_PATH
)

sys.path.insert(
    0,
    PROJECT_ROOT
)


from agent_manager import AgentManager
from task_router import TaskRouter
from agent_registry import load_agents
from reasoning import (
    AgentRouter,
    EvaluationLoop,
    ReasoningEngine,
    ReasoningMemory,
    TaskPlanner,
    WorkflowOrchestrator,
)



class Jarvis:


    def __init__(self, knowledge=None, config=None):

        self.config = self._load_runtime_config(config)

        knowledge_config = self.config.get("knowledge", {})

        self._owns_knowledge = False

        if knowledge is None and knowledge_config.get("enabled", False):

            from knowledge_system import KnowledgeManager

            knowledge = KnowledgeManager(
                storage_path=knowledge_config.get("storage_path")
            )

            self._owns_knowledge = True

        self.knowledge = knowledge

        reasoning_config = self.config.get("reasoning", {})

        planner_config = self.config.get("planner", {})

        evaluation_config = self.config.get("evaluation", {})

        self.reasoning_enabled = reasoning_config.get("enabled", True)

        self.planner_enabled = planner_config.get("enabled", True)

        self.evaluation_enabled = evaluation_config.get("enabled", True)

        self.max_improvement_iterations = evaluation_config.get(
            "max_improvement_iterations",
            1
        )

        self.agent_manager = AgentManager()

        self.task_router = TaskRouter()

        self.register_agents()

        self.reasoning_engine = ReasoningEngine()

        self.agent_router = AgentRouter(
            self.agent_manager
        )

        self.task_planner = TaskPlanner(
            self.agent_router
        )

        self.workflow_orchestrator = WorkflowOrchestrator(
            self.agent_manager
        )

        self.reasoning_memory = ReasoningMemory(
            reasoning_config.get(
                "memory_path",
                ".jarvis/reasoning_memory.json"
            )
        )

        self.evaluation_loop = EvaluationLoop(
            self.agent_manager,
            quality_threshold=evaluation_config.get(
                "quality_threshold",
                7
            )
        )



    def register_agents(self):

        for agent in load_agents(self.knowledge):

            self.agent_manager.register_agent(
                agent
            )



    def process_request(
        self,
        request
    ):

        agent_name = self.task_router.route(
            request
        )


        return self.agent_manager.send_task(
            agent_name,
            request
        )


    def process_workflow(
        self,
        request,
        evaluate=True
    ):
        """Plan and execute a complex request through the Stone 5 layer.

        The original ``process_request`` single-agent path remains unchanged.
        """

        if not self.reasoning_enabled:

            raise RuntimeError(
                "Reasoning workflows are disabled by configuration."
            )

        if not self.planner_enabled:

            raise RuntimeError(
                "Task planning is disabled by configuration."
            )

        strategy = self.reasoning_engine.analyze(
            request
        )

        tasks = self.task_planner.create_plan(
            strategy
        )

        state = self.workflow_orchestrator.execute(
            tasks
        )

        self.reasoning_memory.record_workflow(
            state,
            strategy
        )

        evaluation = None

        final_response = None

        artifact_task = next(
            (
                task
                for task in reversed(tasks)
                if task.id in state.completed_tasks
                and task.required_agent != "reviewer_agent"
            ),
            None
        )

        review_task = next(
            (
                task
                for task in reversed(tasks)
                if task.id in state.completed_tasks
                and task.required_agent == "reviewer_agent"
            ),
            None
        )

        if artifact_task is not None:

            final_response = state.outputs[artifact_task.id]

        if (
            evaluate
            and self.evaluation_enabled
            and artifact_task is not None
        ):

            reviewer_feedback = (
                state.outputs[review_task.id]
                if review_task is not None
                else None
            )

            evaluation_request = (
                f"{request}\nReviewer feedback: "
                f"{json.dumps(reviewer_feedback, default=str, sort_keys=True)}"
            )

            evaluation_cycle = self.evaluation_loop.evaluate_and_improve(
                state.outputs[artifact_task.id],
                artifact_task.required_agent,
                evaluation_request,
                max_iterations=self.max_improvement_iterations
            )

            final_response = evaluation_cycle["final_output"]

            evaluation = evaluation_cycle["evaluations"][-1]

        return {
            "strategy": strategy.to_dict(),
            "tasks": [task.to_dict() for task in tasks],
            "workflow": state.to_dict(),
            "evaluation": evaluation,
            "final_response": final_response
        }


    def close(self):
        """Close a knowledge manager created by this Jarvis instance."""

        if self._owns_knowledge and self.knowledge is not None:

            self.knowledge.close()


    @staticmethod
    def _load_runtime_config(config):
        """Load runtime configuration from a mapping or YAML path."""

        if isinstance(config, dict):

            return config

        config_path = Path(config or os.path.join(PROJECT_ROOT, "jarvis_config.yaml"))

        with config_path.open("r", encoding="utf-8") as config_file:

            return yaml.safe_load(config_file) or {}
