import os
import sys
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

        # Core Kernel path (Stone 1 foundation)
        core_kernel_path = os.path.join(project_root, "01_CORE_KERNEL")

        if core_kernel_path not in sys.path:
            sys.path.insert(0, core_kernel_path)

        # Legacy AI Agents compatibility path
        agents_legacy_path = os.path.join(project_root, "02_AI_AGENTS", "legacy")

        if agents_legacy_path not in sys.path:
            sys.path.insert(0, agents_legacy_path)
        
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
        
        # 9. Latex Engine (Stone 13A)
        # Add 05_LATEX_ENGINE to path explicitly
        
        latex_engine_path = os.path.join(project_root, "05_LATEX_ENGINE")
        if latex_engine_path not in sys.path:
            sys.path.insert(0, latex_engine_path)
            
        from latex_engine import LatexCompiler
        registry.register("latex_compiler", LatexCompiler())
        
        # 10. Build Orchestration (Stone 13B)
        build_orchestration_path = os.path.join(project_root, "06_BUILD_ORCHESTRATION")
        if build_orchestration_path not in sys.path:
            sys.path.insert(0, build_orchestration_path)
            
        from build_orchestration import BuildOrchestrator
        build_orchestrator = BuildOrchestrator(
            compiler=registry.get("latex_compiler"),
            event_bus=registry.get("event_bus")
        )
        registry.register("build_orchestrator", build_orchestrator)
        
        # 11. Thesis Intelligence Layer (Stone 14)
        intelligence_path = os.path.join(project_root, "07_THESIS_INTELLIGENCE")
        if intelligence_path not in sys.path:
            sys.path.insert(0, intelligence_path)
            
        from intelligence_core import LLMGateway, MemoryGateway, AgentRuntimeManager, IntelligenceOrchestrator
        
        llm_gateway = LLMGateway(provider=None)  # stub mode; replace with live provider later
        memory_gateway = MemoryGateway(knowledge_manager=None)  # wired to KnowledgeManager when available
        
        agent_runtime = AgentRuntimeManager(
            build_orchestrator=registry.get("build_orchestrator"),
            llm_gateway=llm_gateway,
            memory_gateway=memory_gateway
        )
        registry.register("llm_gateway", llm_gateway)
        registry.register("memory_gateway", memory_gateway)
        registry.register("agent_runtime", agent_runtime)
        
        intelligence_orchestrator = IntelligenceOrchestrator(
            event_bus=registry.get("event_bus"),
            agent_runtime=agent_runtime
        )
        registry.register("intelligence_orchestrator", intelligence_orchestrator)
        
        # 12. Thesis Session Layer (Stone 15)
        session_path = os.path.join(project_root, "08_THESIS_SESSION")
        if session_path not in sys.path:
            sys.path.insert(0, session_path)
            
        from thesis_session import SafeAgentFileAccess, ThesisSessionManager, SystemActivator
        
        file_access = SafeAgentFileAccess(thesis_root=project_root)
        registry.register("file_access", file_access)
        
        session_manager = ThesisSessionManager(
            event_bus=registry.get("event_bus"),
            thesis_root=project_root
        )
        registry.register("session_manager", session_manager)
        
        # 13. Thesis Knowledge Layer (Stone 16)
        knowledge_path = os.path.join(project_root, "09_THESIS_KNOWLEDGE")
        if knowledge_path not in sys.path:
            sys.path.insert(0, knowledge_path)
            
        from thesis_knowledge import ThesisIndexer, ContextBuilder, ContextGateway, CopilotBridge
        
        indexer = ThesisIndexer(
            event_bus=registry.get("event_bus"),
            file_access=file_access,
            session_id=session_manager.get_session().session_id
        )
        registry.register("thesis_indexer", indexer)
        
        copilot_bridge = CopilotBridge(academic_copilot=registry.get("academic_copilot"))
        registry.register("copilot_bridge", copilot_bridge)
        
        context_builder = ContextBuilder()
        
        context_gateway = ContextGateway(
            indexer=indexer,
            bridge=copilot_bridge,
            builder=context_builder
        )
        registry.register("context_gateway", context_gateway)

        # 14. Academic Agent Cohort (Stone 17)
        agent_cohort_path = os.path.join(project_root, "10_ACADEMIC_AGENTS")
        if agent_cohort_path not in sys.path:
            sys.path.insert(0, agent_cohort_path)
            
        from academic_agents.orchestrator import AcademicAgentOrchestrator
        from academic_agents.planner import PlannerAgent
        from academic_agents.writer import WriterAgent
        from academic_agents.reviewer import ReviewerAgent
        from academic_agents.builder import BuilderAgent
        
        cohort_orchestrator = AcademicAgentOrchestrator(
            event_bus=registry.get("event_bus"),
            runtime=registry.get("agent_runtime")
        )
        
        cohort_orchestrator.register_agent(PlannerAgent())
        cohort_orchestrator.register_agent(WriterAgent())
        cohort_orchestrator.register_agent(ReviewerAgent())
        cohort_orchestrator.register_agent(BuilderAgent())
        
        registry.register("academic_agent_orchestrator", cohort_orchestrator)

        # 15. Academic Workflow Orchestrator (Stone 18)
        workflow_orchestrator_path = os.path.join(project_root, "11_WORKFLOW_ORCHESTRATOR")
        if workflow_orchestrator_path not in sys.path:
            sys.path.insert(0, workflow_orchestrator_path)
            
        from workflow.persistence import WorkflowPersistence
        from workflow.orchestrator import WorkflowOrchestrator
        
        session_root = os.path.join(project_root, "thesis_root") # Actually it's usually inside thesis_root, but project_root is fine for persistence init.
        workflow_persistence = WorkflowPersistence(project_root)
        
        thesis_workflow_orchestrator = WorkflowOrchestrator(
            event_bus=registry.get("event_bus"),
            agent_orchestrator=cohort_orchestrator,
            persistence=workflow_persistence
        )
        registry.register("thesis_workflow_orchestrator", thesis_workflow_orchestrator)

        # 16. Academic Quality Layer (Stone 19)
        quality_path = os.path.join(project_root, "12_ACADEMIC_QUALITY")
        if quality_path not in sys.path:
            sys.path.insert(0, quality_path)
            
        from quality_core.history import QualityHistoryManager
        from quality_core.evaluator import QualityEvaluator
        from quality_core.gateway import QualityGate
        
        quality_history = QualityHistoryManager(workspace_root=project_root)
        quality_evaluator = QualityEvaluator(
            runtime=registry.get("agent_runtime"),
            history_manager=quality_history
        )
        quality_gate = QualityGate(
            evaluator=quality_evaluator,
            workflow_orchestrator=thesis_workflow_orchestrator
        )
        registry.register("quality_history", quality_history)
        registry.register("quality_evaluator", quality_evaluator)
        registry.register("quality_gate", quality_gate)

        # 17. Research Intelligence Layer (Stone 20)
        research_path = os.path.join(project_root, "20_RESEARCH_INTELLIGENCE")
        if research_path not in sys.path:
            sys.path.insert(0, research_path)
            
        from research_core.gateway import ResearchGateway
        
        # Need session_id, getting it from session_manager
        current_session = session_manager.get_session()
        research_gateway = ResearchGateway(
            workspace_root=project_root,
            session_id=current_session.session_id
        )
        registry.register("research_gateway", research_gateway)

        # 18. Thesis Reasoning Layer (Stone 21)
        reasoning_core_path = os.path.join(project_root, "21_THESIS_REASONING")
        if reasoning_core_path not in sys.path:
            sys.path.insert(0, reasoning_core_path)
            
        from reasoning_core.gateway import ReasoningGateway
        
        reasoning_gateway = ReasoningGateway(
            research_gateway=research_gateway,
            context_gateway=registry.get("context_gateway")
        )
        registry.register("reasoning_gateway", reasoning_gateway)

        # 19. Academic Memory Layer (Stone 22)
        memory_core_path = os.path.join(project_root, "13_ACADEMIC_MEMORY")
        if memory_core_path not in sys.path:
            sys.path.insert(0, memory_core_path)
            
        from academic_memory.gateway import AcademicMemoryGateway
        
        academic_memory_gateway = AcademicMemoryGateway(
            workspace_root=project_root,
            session_id=current_session.session_id
        )
        registry.register("academic_memory_gateway", academic_memory_gateway)
        
        # Subscribe Memory to EventBus
        event_bus = registry.get("event_bus")
        event_bus.subscribe("workflow_completed", academic_memory_gateway.handle_workflow_event)

        # 20. Thesis Production Pipeline Layer (Stone 23)
        pipeline_core_path = os.path.join(project_root, "14_THESIS_PIPELINE")
        if pipeline_core_path not in sys.path:
            sys.path.insert(0, pipeline_core_path)
            
        from pipeline_core.pipeline_manager import PipelineManager
        
        thesis_pipeline_manager = PipelineManager(
            session_id=current_session.session_id,
            event_bus=registry.get("event_bus"),
            file_access=registry.get("file_access")
        )
        registry.register("thesis_pipeline_manager", thesis_pipeline_manager)

        # Activate the system
        SystemActivator.activate(registry)
        
    except Exception as e:
        raise BootstrapError(f"Failed to bootstrap JARVIS OS system dependencies: {str(e)}") from e

    return registry

# Stone 24 compatibility bridge
# Runtime entrypoint wrapper
def boot_system(workspace_root=None):
    """
    Compatibility wrapper for JARVIS Runtime.
    """
    return bootstrap_system(project_root=workspace_root)