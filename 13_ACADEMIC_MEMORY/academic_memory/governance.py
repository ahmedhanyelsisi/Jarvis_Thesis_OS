import re
from typing import Dict, Any
from .exceptions import MemoryGovernanceError

class MemoryGovernance:
    """Enforces boundaries, limits, and sanitizes input to prevent poisoning."""
    
    # Simple regex to catch common prompt injection patterns
    MALICIOUS_PATTERNS = [
        r"ignore previous instructions",
        r"override system",
        r"system prompt",
        r"always approve",
        r"bypass safety"
    ]
    
    MAX_TEXT_LENGTH = 10000

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        if not text:
            return ""
            
        if len(text) > cls.MAX_TEXT_LENGTH:
            raise MemoryGovernanceError(f"Text exceeds maximum memory length of {cls.MAX_TEXT_LENGTH} characters.")
            
        text_lower = text.lower()
        for pattern in cls.MALICIOUS_PATTERNS:
            if re.search(pattern, text_lower):
                raise MemoryGovernanceError("Malicious memory injection detected and blocked.")
                
        return text

    @classmethod
    def validate_session_id(cls, session_id: str, expected_session: str):
        # Prevent cross-session leakage
        if session_id != expected_session:
            raise MemoryGovernanceError(f"Cross-session memory access violation: {session_id} != {expected_session}")
            
    @classmethod
    def sanitize_payload(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitizes dict payloads."""
        clean = {}
        for k, v in payload.items():
            if isinstance(v, str):
                clean[k] = cls.sanitize_text(v)
            elif isinstance(v, dict):
                clean[k] = cls.sanitize_payload(v)
            else:
                clean[k] = v
        return clean
