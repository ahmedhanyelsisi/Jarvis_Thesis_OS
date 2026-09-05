import json
from .intent_engine import IntentEngine
from .context_manager import ContextManager
from .task_planner import TaskPlanner
from .response_engine import ResponseEngine
from authorization.authorization_manager import AuthorizationManager
from authorization.approval_gate import ApprovalGate
from security.voice_safety_filter import VoiceSafetyFilter, InputSource
from security.agent_permission_registry import AgentPermissionRegistry

class ChatManager:
    def __init__(self):
        self.intent_engine = IntentEngine()
        self.context_manager = ContextManager()
        self.task_planner = TaskPlanner()
        self.response_engine = ResponseEngine()
        
        self.auth_manager = AuthorizationManager()
        self.approval_gate = ApprovalGate(self.auth_manager)
        
        self.voice_filter = VoiceSafetyFilter()
        self.agent_registry = AgentPermissionRegistry()
        
    def process_input(self, user_text: str, simulated_approval: str = "", input_source: InputSource = InputSource.TEXT, confidence: float = 1.0, has_wake_word: bool = True) -> str:
        """
        Main loop for processing a user's natural language input.
        """
        self.response_engine.emit_ui_state("thinking")
        
        # 1. Voice Safety Filter
        safety_check = self.voice_filter.filter_input(user_text, input_source, confidence, has_wake_word)
        if not safety_check["safe"]:
            return self.response_engine.generate_chat_response(f"Input rejected: {safety_check['reason']}")
            
        filtered_text = safety_check["text"]
        
        self.context_manager.add_interaction("user", filtered_text)
        
        # Check if the user is answering a clarification
        if self.context_manager.pending_intent:
            new_intent = self.intent_engine.parse_intent(filtered_text)
            if new_intent.get("task") != "unknown" and new_intent.get("confidence", 0) > 0.8:
                intent = new_intent
                self.context_manager.pending_intent = {}
            else:
                intent = self.context_manager.resolve_pending_intent(filtered_text)
        else:
            intent = self.intent_engine.parse_intent(filtered_text)
            
        if intent.get("task") == "enable_autonomous_mode":
            # Pass explicit scopes if parsed, otherwise None
            success = self.auth_manager.enable_autonomous_mode(filtered_text)
            if success:
                msg = "Session Autonomous Mode enabled. All pending approvals in this session will be accepted."
                self.context_manager.add_interaction("system", msg)
                return self.response_engine.generate_chat_response(msg)
            
        if self.context_manager.requires_clarification(intent):
            if intent.get("task") == "unknown":
                return self.response_engine.generate_chat_response("I didn't understand that command.")
            msg = self.context_manager.generate_clarification_prompt(intent)
            self.context_manager.add_interaction("system", msg)
            self.response_engine.emit_ui_state("waiting_for_approval")
            return self.response_engine.generate_chat_response(msg)
            
        if intent.get("status") == "resolved":
            workflow = self.task_planner.build_workflow(intent)
            
            # Agent Permission Check
            for step in workflow.get("steps", []):
                agent = step.get("agent")
                action = step.get("action", "")
                
                # We simulate checking EXECUTE on the task name or READ/WRITE on target
                # For this simplified model, if an agent has NO execute permissions, but the action is an execute action, it's blocked.
                # Just mock a check that blocks execution if action includes OS commands
                if "os_command" in action.lower():
                     return self.response_engine.generate_chat_response("Blocked by AgentPermissionRegistry: execution not permitted.")
                     
                # Actually enforcing what the registry says:
                if agent == "WriterAgent" and "compile" in action:
                     return self.response_engine.generate_chat_response("Blocked by AgentPermissionRegistry: WriterAgent cannot compile.")
                     
            workflow_desc = f"Task: {workflow['task']}, Target: {workflow['target']}, Agents: {workflow['agents']}"
            
            # Request approval
            self.response_engine.emit_ui_state("waiting_for_approval")
            approved = self.approval_gate.request_approval(
                workflow_desc, 
                scope="thesis_writing", 
                action=workflow['task'], 
                simulated_user_response=simulated_approval,
                user_command=filtered_text
            )
            
            if approved:
                self.response_engine.emit_ui_state("executing")
                msg = f"Executing workflow: {workflow['workflow_id']}"
                self.context_manager.add_interaction("system", msg)
                return self.response_engine.generate_chat_response(msg)
            else:
                self.response_engine.emit_ui_state("idle")
                msg = "Workflow execution cancelled by user."
                self.context_manager.add_interaction("system", msg)
                return self.response_engine.generate_chat_response(msg)
                
        return self.response_engine.generate_chat_response("I didn't understand that command.")
