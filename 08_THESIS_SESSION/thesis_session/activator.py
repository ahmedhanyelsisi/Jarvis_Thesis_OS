class SystemActivator:
    """
    Wires live systems and boots the event loops for JARVIS OS.
    Called at the very end of bootstrap after all dependencies are registered.
    """
    @staticmethod
    def activate(registry) -> None:
        # 1. Start the Intelligence Orchestrator
        intelligence_orchestrator = registry.get("intelligence_orchestrator")
        if intelligence_orchestrator:
            intelligence_orchestrator.activate()
            
        # 2. Inject SafeAgentFileAccess and ContextGateway into AgentRuntimeManager for Context prototype
        agent_runtime = registry.get("agent_runtime")
        file_access = registry.get("file_access")
        context_gateway = registry.get("context_gateway")
        
        if agent_runtime and file_access:
            # We monkey-patch the build_context method to inject file methods
            # Because Stone 14's AgentContext didn't originally have them.
            # We are fulfilling the user's architectural requirement by modifying the runtime's context factory.
            
            original_build = agent_runtime.build_context
            
            def enhanced_build_context(agent_role: str):
                ctx = original_build(agent_role)
                # Monkey-patch the context object with the new safe methods
                ctx.read_thesis_file = file_access.read_file
                ctx.write_thesis_file = file_access.write_file
                
                # Stone 16 methods
                if context_gateway:
                    ctx.search_thesis = context_gateway.search_thesis
                    ctx.get_document_structure = context_gateway.get_document_structure
                    ctx.build_context = context_gateway.build_context
                    
                # Stone 21 methods
                reasoning_gateway = registry.get("reasoning_gateway")
                if reasoning_gateway:
                    ctx.analyze_argument = reasoning_gateway.analyze_argument
                    ctx.map_evidence = reasoning_gateway.map_evidence
                    ctx.detect_contradictions = reasoning_gateway.detect_contradictions
                    ctx.synthesize_reasoning = reasoning_gateway.synthesize_reasoning
                
                return ctx
                
            agent_runtime.build_context = enhanced_build_context
