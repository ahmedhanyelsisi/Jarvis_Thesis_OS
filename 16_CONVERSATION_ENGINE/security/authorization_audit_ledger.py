import hashlib
import time
import json
from typing import Dict, Any, List

class AuthorizationAuditLedger:
    def __init__(self):
        self._ledger: List[Dict[str, Any]] = []
        self._last_hash = "0" * 64

    def _hash_event(self, event_data: str) -> str:
        return hashlib.sha256(event_data.encode('utf-8')).hexdigest()

    def record_event(self, session_id: str, user_command: str, detected_intent: str,
                     authorization_state: str, active_scope: str, affected_subsystem: str, 
                     execution_result: str, caller: str) -> bool:
        """
        Record authorization event.
        Requires caller string verification (simple simulated check for 'AuthorizationManager').
        """
        if caller != "AuthorizationManager":
            raise PermissionError("Only AuthorizationManager can write to the ledger.")

        event = {
            "timestamp": time.time(),
            "session_id": session_id,
            "user_command": user_command,
            "detected_intent": detected_intent,
            "authorization_state": authorization_state,
            "active_scope": active_scope,
            "affected_subsystem": affected_subsystem,
            "execution_result": execution_result,
            "previous_hash": self._last_hash
        }
        
        event_json = json.dumps(event, sort_keys=True)
        event_hash = self._hash_event(event_json)
        event["event_hash"] = event_hash
        
        self._ledger.append(event)
        self._last_hash = event_hash
        return True

    def verify_integrity(self) -> bool:
        """
        Tamper detection.
        """
        expected_prev_hash = "0" * 64
        for event in self._ledger:
            if event["previous_hash"] != expected_prev_hash:
                return False
                
            # Recreate event data without the hash
            event_copy = dict(event)
            stored_hash = event_copy.pop("event_hash")
            event_json = json.dumps(event_copy, sort_keys=True)
            computed_hash = self._hash_event(event_json)
            
            if computed_hash != stored_hash:
                return False
            expected_prev_hash = stored_hash
            
        return True
