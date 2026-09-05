import time
from typing import List, Optional

class ScopedAutonomousManager:
    SUPPORTED_SCOPES = ["thesis_writing", "research", "review", "compilation", "documentation"]
    
    def __init__(self):
        self._active_scopes: List[str] = []
        self._ttl_expiry: Optional[float] = None
        
    def enable_scopes(self, scopes: List[str], ttl_seconds: int = 3600):
        """
        Enables autonomous mode for specific scopes.
        """
        valid_scopes = [s for s in scopes if s in self.SUPPORTED_SCOPES]
        if valid_scopes:
            self._active_scopes = valid_scopes
            self._ttl_expiry = time.time() + ttl_seconds
            return True
        return False
        
    def is_scope_active(self, scope: str) -> bool:
        if not self._active_scopes or not self._ttl_expiry:
            return False
        if time.time() > self._ttl_expiry:
            self.reset()
            return False
        return scope in self._active_scopes
        
    def is_action_blocked(self, action: str) -> bool:
        """
        Hard block on dangerous OS or external changes regardless of scope.
        """
        blocked_keywords = ["os_command", "file_deletion", "system_modification", "external_change", "delete", "rm", "sudo"]
        for kw in blocked_keywords:
            if kw in action.lower():
                return True
        return False
        
    def reset(self):
        self._active_scopes = []
        self._ttl_expiry = None

    def get_active_scopes(self) -> List[str]:
        if self._ttl_expiry and time.time() > self._ttl_expiry:
            self.reset()
        return list(self._active_scopes)
