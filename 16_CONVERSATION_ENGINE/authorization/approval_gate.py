from .authorization_manager import AuthorizationManager

class ApprovalGate:
    def __init__(self, auth_manager: AuthorizationManager):
        self.auth_manager = auth_manager
        
    def request_approval(self, workflow_description: str, scope: str = "thesis_writing", action: str = "", critical: bool = False, simulated_user_response: str = "", user_command: str = "") -> bool:
        """
        Hybrid approval: workflow-level by default, requires explicit user response or active scoped autonomy.
        """
        if self.auth_manager.is_autonomous_for_scope(scope, action):
            print(f"[DAL] Scoped Autonomous mode active ({scope}). Automatically approving: {workflow_description}")
            self.auth_manager.log_workflow_approval(user_command, "workflow_execution", scope, "APPROVED_AUTONOMOUS")
            return True
            
        print(f"[DAL] CONTROLLED MODE. Approval requested for: {workflow_description}")
        if critical:
            print("[DAL] WARNING: This is a critical operation.")
            
        response = simulated_user_response.strip().lower()
        
        if response in ["yes", "approve", "y", "go ahead"]:
            self.auth_manager.log_workflow_approval(user_command, "workflow_execution", scope, "APPROVED")
            return True
            
        self.auth_manager.log_workflow_approval(user_command, "workflow_execution", scope, "REJECTED")
        return False
