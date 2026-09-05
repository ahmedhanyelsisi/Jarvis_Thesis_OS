from typing import List, Dict, Any

class AgentPermissionRegistry:
    def __init__(self):
        # Strict explicit permissions. No inheritance.
        self._registry = {
            "ResearchAgent": {
                "READ": ["papers", "literature"],
                "WRITE": ["research_notes"],
                "EXECUTE": []
            },
            "WriterAgent": {
                "READ": ["approved_thesis_context"],
                "WRITE": ["draft_files"],
                "EXECUTE": []
            },
            "ReviewerAgent": {
                "READ": ["drafts"],
                "WRITE": ["review_comments"],
                "EXECUTE": []
            },
            "BuildAgent": {
                "READ": ["latex_files"],
                "WRITE": ["build_outputs"],
                "EXECUTE": ["compile"]
            }
        }
        
    def check_permission(self, agent_name: str, action_type: str, resource: str) -> bool:
        """
        Check if an agent has permission to perform an action on a resource.
        """
        action_type = action_type.upper()
        
        # Hard block on system-level changes
        blocked_resources = ["authorization", "autonomy", "configuration", "system"]
        if resource.lower() in blocked_resources:
            return False
            
        if agent_name not in self._registry:
            return False
            
        permissions = self._registry[agent_name].get(action_type, [])
        return resource in permissions
