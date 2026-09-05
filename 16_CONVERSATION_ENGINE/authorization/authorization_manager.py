import uuid
from typing import Any, List
from security.authorization_audit_ledger import AuthorizationAuditLedger
from security.scoped_autonomous_manager import ScopedAutonomousManager

class AuthorizationManager:
    def __init__(self):
        self.ledger = AuthorizationAuditLedger()
        self.scoped_manager = ScopedAutonomousManager()
        self.session_id = str(uuid.uuid4())
        
    def enable_autonomous_mode(self, explicit_command: str, scopes: List[str] = None) -> bool:
        """
        Activates SCOPED AUTONOMOUS MODE.
        """
        if scopes is None:
            scopes = []
            
        valid_commands = ["approve all thesis operations", "enable autonomous mode", "continue without asking", "jarvis approve all"]
        if explicit_command.lower().strip() in valid_commands:
            # Default fallback scopes if none provided
            if not scopes:
                scopes = ["thesis_writing", "research", "review", "compilation"]
                
            success = self.scoped_manager.enable_scopes(scopes)
            
            self.ledger.record_event(
                session_id=self.session_id,
                user_command=explicit_command,
                detected_intent="enable_autonomous_mode",
                authorization_state="AUTONOMOUS_MODE_ENABLED",
                active_scope=",".join(scopes),
                affected_subsystem="DynamicAuthorizationLayer",
                execution_result="SUCCESS" if success else "FAILED",
                caller="AuthorizationManager"
            )
            return success
            
        self.ledger.record_event(
            session_id=self.session_id,
            user_command=explicit_command,
            detected_intent="enable_autonomous_mode",
            authorization_state="CONTROLLED_MODE",
            active_scope="none",
            affected_subsystem="DynamicAuthorizationLayer",
            execution_result="REJECTED_INVALID_COMMAND",
            caller="AuthorizationManager"
        )
        return False
        
    def end_session(self):
        self.scoped_manager.reset()
        self.session_id = str(uuid.uuid4())
        
    def is_autonomous_for_scope(self, scope: str, action: str = "") -> bool:
        if self.scoped_manager.is_action_blocked(action):
            return False
        return self.scoped_manager.is_scope_active(scope)
        
    def log_workflow_approval(self, user_command: str, intent: str, scope: str, result: str):
        self.ledger.record_event(
            session_id=self.session_id,
            user_command=user_command,
            detected_intent=intent,
            authorization_state="EXPLICIT_APPROVAL" if result == "APPROVED" else "REJECTED",
            active_scope=scope,
            affected_subsystem="WorkflowExecution",
            execution_result=result,
            caller="AuthorizationManager"
        )
