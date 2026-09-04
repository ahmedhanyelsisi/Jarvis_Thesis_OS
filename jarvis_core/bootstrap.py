import os
from pathlib import Path
import yaml
from typing import Any, Dict, Optional

from .registry import ServiceRegistry
from .event_bus import EventBus

class BootstrapError(Exception):
    """Raised when system dependencies fail to initialize."""
    pass

# We use delayed imports to avoid circular dependencies and keep bootstrap clean
def bootstrap_system(
    knowledge: Optional[Any] = None, 
    config: Optional[Dict[str, Any]] = None, 
    project_root: Optional[str] = None
) -> ServiceRegistry:
    """Initialize system dependencies and return the service registry."""
    
    try:
        if project_root is None:
            # Fallback to calculating from current file if not provided
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        registry = ServiceRegistry()
        
        # 1. Event Bus
        event_bus = EventBus()
        registry.register("event_bus", event_bus)
        
        # 2. Config
        if not isinstance(config, dict):
            config_path = Path(config or os.path.join(project_root, "jarvis_config.yaml"))
            with config_path.open("r", encoding="utf-8") as config_file:
                config = yaml.safe_load(config_file) or {}
        registry.register("config", config)
        
        # 3. Memory Manager
        memory_config = config.get("memory", {})
        memory_database_path = Path(
            memory_config.get("database_path", os.path.join(project_root, "memory_database.sqlite"))
        )
        if not memory_database_path.is_absolute():
            memory_database_path = Path(project_root) / memory_database_path

        from memory import MemoryManager
        memory_manager = MemoryManager(
            database_path=memory_database_path,
            enabled=memory_config.get("enabled", bool(memory_config)),
            max_results=memory_config.get("max_results", 10),
            importance_threshold=memory_config.get("importance_threshold", 0.0),
        )
        registry.register("memory_manager", memory_manager)
        
        # 4. Knowledge System
        owns_knowledge = False
        knowledge_config = config.get("knowledge", {})
        if knowledge is None and knowledge_config.get("enabled", False):
            from knowledge_system import KnowledgeManager
            knowledge = KnowledgeManager(storage_path=knowledge_config.get("storage_path"))
            owns_knowledge = True
        
        registry.register("knowledge", knowledge)
        registry.register("owns_knowledge", owns_knowledge)
        
        # 5. Core Utilities and Flags
        reasoning_config = config.get("reasoning", {})
        planner_config = config.get("planner", {})
        evaluation_config = config.get("evaluation", {})
        
        registry.register("reasoning_enabled", reasoning_config.get("enabled", True))
        registry.register("planner_enabled", planner_config.get("enabled", True))
        registry.register("evaluation_enabled", evaluation_config.get("enabled", True))
        registry.register("max_improvement_iterations", evaluation_config.get("max_improvement_iterations", 1))
        
        from agent_manager import AgentManager
        from task_router import TaskRouter
        from agent_registry import load_agents
        
        agent_manager = AgentManager()
        task_router = TaskRouter()
        
        for agent in load_agents(knowledge):
            agent_manager.register_agent(agent)
            
        registry.register("agent_manager", agent_manager)
        registry.register("task_router", task_router)
        
        # 6. Academic Modules (Stones 9-12)
        from academic_intelligence import AcademicWorkflowRouter
        from thesis_workspace import ThesisWorkspaceManager
        from academic_copilot import AcademicCopilot
        from academic_workflow import AcademicWorkflow
        
        class KernelProxy:
            def __init__(self, reg):
                self._reg = reg
            def __getattr__(self, name):
                return self._reg.get(name)
                
        kernel_proxy = KernelProxy(registry)
        
        academic_router = AcademicWorkflowRouter(kernel=kernel_proxy)
        registry.register("academic_router", academic_router)
        
        workspace_config = config.get("thesis_workspace", {})
        workspace_root = Path(workspace_config.get("root", project_root))
        if not workspace_root.is_absolute():
            workspace_root = Path(project_root) / workspace_root
            
        thesis_workspace = ThesisWorkspaceManager(workspace_root)
        registry.register("thesis_workspace", thesis_workspace)
        
        academic_copilot = AcademicCopilot(academic_router, thesis_workspace)
        registry.register("academic_copilot", academic_copilot)
        
        academic_workflow = AcademicWorkflow(
            copilot=academic_copilot,
            workspace=thesis_workspace,
            router=academic_router,
        )
        registry.register("academic_workflow", academic_workflow)
        
        # 7. Reasoning & Planning
        from reasoning import (
            AgentRouter,
            EvaluationLoop,
            ReasoningEngine,
            ReasoningMemory,
            TaskPlanner,
            WorkflowOrchestrator,
        )
        
        reasoning_engine = ReasoningEngine()
        agent_router = AgentRouter(agent_manager)
        task_planner = TaskPlanner(agent_router)
        workflow_orchestrator = WorkflowOrchestrator(agent_manager)
        
        reasoning_memory = ReasoningMemory(
            reasoning_config.get("memory_path", ".jarvis/reasoning_memory.json")
        )
        
        evaluation_loop = EvaluationLoop(
            agent_manager,
            quality_threshold=evaluation_config.get("quality_threshold", 7)
        )
        
        registry.register("reasoning_engine", reasoning_engine)
        registry.register("agent_router", agent_router)
        registry.register("task_planner", task_planner)
        registry.register("workflow_orchestrator", workflow_orchestrator)
        registry.register("reasoning_memory", reasoning_memory)
        registry.register("evaluation_loop", evaluation_loop)
        
        # 8. Voice
        voice_config = config.get("voice", {})
        voice_enabled = voice_config.get("enabled", False)
        registry.register("voice_enabled", voice_enabled)
        
        voice_manager = None
        if voice_enabled:
            from voice import VoiceManager
            voice_manager = VoiceManager(kernel_proxy, config=voice_config)
        registry.register("voice_manager", voice_manager)
        
    except Exception as e:
        raise BootstrapError(f"Failed to bootstrap JARVIS OS system dependencies: {str(e)}") from e

    return registry
