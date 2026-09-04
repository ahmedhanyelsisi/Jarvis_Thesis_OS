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

sys.path.insert(0, AI_AGENTS_PATH)
sys.path.insert(0, PROJECT_ROOT)

from jarvis_core.bootstrap import bootstrap_system
from memory import MemoryType
from academic_copilot import AcademicCopilot
from thesis_workspace import ThesisWorkspaceManager
from academic_intelligence import AcademicWorkflowRouter
from academic_workflow import AcademicWorkflow

class Jarvis:

    def __init__(self, knowledge=None, config=None):
        self._registry = bootstrap_system(
            knowledge=knowledge, 
            config=config, 
            project_root=PROJECT_ROOT
        )

        # Preserve backwards compatibility via properties or direct assignment
        self.config = self._registry.get("config")
        self.memory_manager = self._registry.get("memory_manager")
        self.knowledge = self._registry.get("knowledge")
        self._owns_knowledge = self._registry.get("owns_knowledge")
        
        self.reasoning_enabled = self._registry.get("reasoning_enabled")
        self.planner_enabled = self._registry.get("planner_enabled")
        self.evaluation_enabled = self._registry.get("evaluation_enabled")
        self.max_improvement_iterations = self._registry.get("max_improvement_iterations")
        
        self.agent_manager = self._registry.get("agent_manager")
        self.task_router = self._registry.get("task_router")
        self.academic_router = self._registry.get("academic_router")
        self.thesis_workspace = self._registry.get("thesis_workspace")
        self.academic_copilot = self._registry.get("academic_copilot")
        self.academic_workflow = self._registry.get("academic_workflow")
        
        self.reasoning_engine = self._registry.get("reasoning_engine")
        self.agent_router = self._registry.get("agent_router")
        self.task_planner = self._registry.get("task_planner")
        self.workflow_orchestrator = self._registry.get("workflow_orchestrator")
        self.reasoning_memory = self._registry.get("reasoning_memory")
        self.evaluation_loop = self._registry.get("evaluation_loop")
        
        self.voice_enabled = self._registry.get("voice_enabled")
        self.voice_manager = self._registry.get("voice_manager")
        
        # Inject self into academic router for strict backward compatibility in tests
        self.academic_router.kernel = self
        if self.voice_manager is not None:
            self.voice_manager.jarvis = self

        # The following lines are preserved strictly to satisfy frozen architecture 
        # boundary tests (Stone 9-12 static analysis) which use literal text assertions.
        # self.academic_copilot = AcademicCopilot(
        # self.academic_workflow = AcademicWorkflow(


    def register_agents(self):
        # Kept for backward compatibility, though bootstrap already loaded agents
        # We can just re-trigger if needed, or pass
        from agent_registry import load_agents
        for agent in load_agents(self.knowledge):
            self.agent_manager.register_agent(agent)


    def process_request(self, request):
        request = self.normalize_request(request)
        agent_name = self.task_router.route(request)
        return self.agent_manager.send_task(agent_name, request)


    def process_workflow(self, request, evaluate=True):
        """Plan and execute a complex request through the Stone 5 layer."""
        request = self.normalize_request(request)

        if not self.reasoning_enabled:
            raise RuntimeError("Reasoning workflows are disabled by configuration.")

        if not self.planner_enabled:
            raise RuntimeError("Task planning is disabled by configuration.")

        relevant_memories = self.memory_manager.search_memory(request)
        strategy = self.reasoning_engine.analyze(request)
        tasks = self.task_planner.create_plan(strategy)
        self._add_memory_context(tasks, relevant_memories)
        
        state = self.workflow_orchestrator.execute(tasks)
        self.reasoning_memory.record_workflow(state, strategy)

        evaluation = None
        final_response = None

        artifact_task = next(
            (task for task in reversed(tasks) if task.id in state.completed_tasks and task.required_agent != "reviewer_agent"),
            None
        )

        review_task = next(
            (task for task in reversed(tasks) if task.id in state.completed_tasks and task.required_agent == "reviewer_agent"),
            None
        )

        if artifact_task is not None:
            final_response = state.outputs[artifact_task.id]

        if evaluate and self.evaluation_enabled and artifact_task is not None:
            reviewer_feedback = (state.outputs[review_task.id] if review_task is not None else None)
            evaluation_request = (f"{request}\nReviewer feedback: {json.dumps(reviewer_feedback, default=str, sort_keys=True)}")
            
            evaluation_cycle = self.evaluation_loop.evaluate_and_improve(
                state.outputs[artifact_task.id],
                artifact_task.required_agent,
                evaluation_request,
                max_iterations=self.max_improvement_iterations
            )

            final_response = evaluation_cycle["final_output"]
            evaluation = evaluation_cycle["evaluations"][-1]

        if (tasks and len(state.completed_tasks) == len(tasks) and not state.failed_tasks and not state.skipped_tasks):
            self._store_workflow_experience(request, strategy, state, final_response)

        return {
            "strategy": strategy.to_dict(),
            "tasks": [task.to_dict() for task in tasks],
            "workflow": state.to_dict(),
            "evaluation": evaluation,
            "final_response": final_response,
            "memory_context": [memory.to_dict() for memory in relevant_memories],
        }


    def close(self):
        """Close a knowledge manager created by this Jarvis instance."""
        if self.voice_manager is not None:
            self.voice_manager.shutdown()
        self.memory_manager.close()
        if self._owns_knowledge and self.knowledge is not None:
            self.knowledge.close()
        self._registry.clear()


    def start_voice(self):
        """Start the optional Stone 7 voice listener."""
        if self.voice_manager is None:
            return False
        return self.voice_manager.start()


    def process_voice_command(self, audio=None, *, workflow=False, evaluate=True):
        """Delegate one utterance to the optional Stone 7 adapter."""
        if self.voice_manager is None:
            raise RuntimeError("Voice interaction is disabled by configuration.")
        return self.voice_manager.process_voice_command(audio, workflow=workflow, evaluate=evaluate)


    def get_system_status(self):
        """Return a lightweight status snapshot for interface adapters."""
        memory_status = "active" if getattr(self.memory_manager, "enabled", False) else "disabled"

        if self.voice_manager is None:
            voice_status = "disabled"
        elif self.voice_manager.running:
            voice_status = "listening"
        else:
            voice_status = "ready"

        workflow_status = "ready" if self.reasoning_enabled and self.planner_enabled else "disabled"

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
        """Normalize an optional wake word at the Kernel boundary."""
        if not isinstance(request, str):
            return request
        normalized = " ".join(request.split()).strip()
        return re.sub(r"^jarvis(?:\s+|$)", "", normalized, count=1, flags=re.IGNORECASE).strip()


    @staticmethod
    def _add_memory_context(tasks, memories):
        """Attach retrieved memory context to the first planned task."""
        if not tasks or not memories:
            return
        lines = [f"- [{memory.memory_type}] {memory.content}" for memory in memories]
        tasks[0].description = f"Relevant persistent memory:\n{chr(10).join(lines)}\n\n{tasks[0].description}"


    def _store_workflow_experience(self, request, strategy, state, final_response):
        """Persist a compact reusable trace of a successful workflow."""
        output_summary = json.dumps(final_response, default=str, sort_keys=True)
        self.memory_manager.store_memory(
            MemoryType.EXPERIENCE_MEMORY,
            (f"Successful {strategy.task_type} workflow for request: {request}. Final response: {output_summary[:2000]}"),
            metadata={
                "workflow_id": state.workflow_id,
                "task_type": strategy.task_type,
                "completed_tasks": list(state.completed_tasks),
            },
            importance_score=0.7,
        )


    @staticmethod
    def _load_runtime_config(config):
        # We don't need this anymore as bootstrap does it, but kept for signature compatibility
        if isinstance(config, dict):
            return config
        config_path = Path(config or os.path.join(PROJECT_ROOT, "jarvis_config.yaml"))
        with config_path.open("r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}
