import sys
import os
import json
import re
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
from memory import MemoryManager, MemoryType
from academic_intelligence import AcademicWorkflowRouter



class Jarvis:


    def __init__(self, knowledge=None, config=None):

        self.config = self._load_runtime_config(config)

        memory_config = self.config.get("memory", {})

        memory_database_path = Path(
            memory_config.get(
                "database_path",
                os.path.join(PROJECT_ROOT, "memory_database.sqlite")
            )
        )

        if not memory_database_path.is_absolute():

            memory_database_path = Path(PROJECT_ROOT) / memory_database_path

        self.memory_manager = MemoryManager(
            database_path=memory_database_path,
            enabled=memory_config.get("enabled", bool(memory_config)),
            max_results=memory_config.get("max_results", 10),
            importance_threshold=memory_config.get("importance_threshold", 0.0),
        )

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

        # Stone 9 adapter: academic state is owned by ARIL; Kernel APIs remain
        # the only boundary used for fallback command handling.
        self.academic_router = AcademicWorkflowRouter(kernel=self)

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

        voice_config = self.config.get("voice", {})

        self.voice_enabled = voice_config.get("enabled", False)

        self.voice_manager = None

        if self.voice_enabled:

            from voice import VoiceManager

            self.voice_manager = VoiceManager(
                self,
                config=voice_config
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

        request = self.normalize_request(request)

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

        request = self.normalize_request(request)

        if not self.reasoning_enabled:

            raise RuntimeError(
                "Reasoning workflows are disabled by configuration."
            )

        if not self.planner_enabled:

            raise RuntimeError(
                "Task planning is disabled by configuration."
            )

        relevant_memories = self.memory_manager.search_memory(
            request
        )

        strategy = self.reasoning_engine.analyze(
            request
        )

        tasks = self.task_planner.create_plan(
            strategy
        )

        self._add_memory_context(
            tasks,
            relevant_memories
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

        if (
            tasks
            and len(state.completed_tasks) == len(tasks)
            and not state.failed_tasks
            and not state.skipped_tasks
        ):

            self._store_workflow_experience(
                request,
                strategy,
                state,
                final_response
            )

        return {
            "strategy": strategy.to_dict(),
            "tasks": [task.to_dict() for task in tasks],
            "workflow": state.to_dict(),
            "evaluation": evaluation,
            "final_response": final_response,
            "memory_context": [
                memory.to_dict()
                for memory in relevant_memories
            ],
        }


    def close(self):
        """Close a knowledge manager created by this Jarvis instance."""

        if self.voice_manager is not None:

            self.voice_manager.shutdown()

        self.memory_manager.close()

        if self._owns_knowledge and self.knowledge is not None:

            self.knowledge.close()


    def start_voice(self):
        """Start the optional Stone 7 voice listener."""

        if self.voice_manager is None:

            return False

        return self.voice_manager.start()


    def process_voice_command(
        self,
        audio=None,
        *,
        workflow=False,
        evaluate=True
    ):
        """Delegate one utterance to the optional Stone 7 adapter."""

        if self.voice_manager is None:

            raise RuntimeError(
                "Voice interaction is disabled by configuration."
            )

        return self.voice_manager.process_voice_command(
            audio,
            workflow=workflow,
            evaluate=evaluate
        )


    def get_system_status(self):
        """Return a lightweight status snapshot for interface adapters."""

        memory_status = (
            "active"
            if getattr(self.memory_manager, "enabled", False)
            else "disabled"
        )

        if self.voice_manager is None:

            voice_status = "disabled"

        elif self.voice_manager.running:

            voice_status = "listening"

        else:

            voice_status = "ready"

        workflow_status = (
            "ready"
            if self.reasoning_enabled and self.planner_enabled
            else "disabled"
        )

        return {
            "kernel": "active",
            "agents": len(self.agent_manager.list_agents()),
            "memory": memory_status,
            "voice": voice_status,
            "workflow": workflow_status,
            "academic_intelligence": "ready",
        }


    @staticmethod
    def normalize_request(request):
        """Normalize an optional wake word at the Kernel boundary.

        ARIL and existing routers receive only the cleaned command. Non-string
        values are preserved for backwards-compatible downstream validation.
        """
        if not isinstance(request, str):
            return request
        normalized = " ".join(request.split()).strip()
        return re.sub(r"^jarvis(?:\s+|$)", "", normalized, count=1, flags=re.IGNORECASE).strip()


    @staticmethod
    def _add_memory_context(tasks, memories):
        """Attach retrieved memory context to the first planned task."""

        if not tasks or not memories:

            return

        lines = [
            f"- [{memory.memory_type}] {memory.content}"
            for memory in memories
        ]

        tasks[0].description = (
            f"Relevant persistent memory:\n{chr(10).join(lines)}\n\n"
            f"{tasks[0].description}"
        )


    def _store_workflow_experience(
        self,
        request,
        strategy,
        state,
        final_response
    ):
        """Persist a compact reusable trace of a successful workflow."""

        output_summary = json.dumps(
            final_response,
            default=str,
            sort_keys=True
        )

        self.memory_manager.store_memory(
            MemoryType.EXPERIENCE_MEMORY,
            (
                f"Successful {strategy.task_type} workflow for request: {request}. "
                f"Final response: {output_summary[:2000]}"
            ),
            metadata={
                "workflow_id": state.workflow_id,
                "task_type": strategy.task_type,
                "completed_tasks": list(state.completed_tasks),
            },
            importance_score=0.7,
        )


    @staticmethod
    def _load_runtime_config(config):
        """Load runtime configuration from a mapping or YAML path."""

        if isinstance(config, dict):

            return config

        config_path = Path(config or os.path.join(PROJECT_ROOT, "jarvis_config.yaml"))

        with config_path.open("r", encoding="utf-8") as config_file:

            return yaml.safe_load(config_file) or {}
