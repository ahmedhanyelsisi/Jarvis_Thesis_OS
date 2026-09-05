import json
import hashlib
from typing import Dict, Any

class JarvisStateRecovery:
    def __init__(self):
        self.version = "1.0.0"
        self._state_file = "jarvis_recovery_state.json"
        
    def _generate_checksum(self, config: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        
    def save_state(self, config: Dict[str, Any], runtime_state: Dict[str, Any]):
        """
        Save safe runtime state. Never store authorization tokens or autonomous permissions.
        """
        safe_state = {
            "version": self.version,
            "checksum": self._generate_checksum(config),
            "safe_runtime_state": {
                k: v for k, v in runtime_state.items() 
                if k not in ["authorization_tokens", "autonomous_permissions"]
            }
        }
        
        # In a real implementation, this would write to self._state_file
        self._last_saved_state = safe_state
        return True
        
    def recover_state(self) -> Dict[str, Any]:
        """
        Load state after restart. Always defaults to CONTROLLED MODE.
        """
        # Simulated recovery
        recovered = getattr(self, '_last_saved_state', None)
        if not recovered:
            recovered = {"safe_runtime_state": {}}
            
        # Hardcode reset to CONTROLLED MODE
        recovered["safe_runtime_state"]["authorization_mode"] = "CONTROLLED_MODE"
        return recovered
