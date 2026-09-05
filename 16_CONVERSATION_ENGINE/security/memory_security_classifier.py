from enum import Enum
from typing import Dict, Any, List

class MemoryLevel(Enum):
    LEVEL_0_TEMP = 0
    LEVEL_1_SESSION = 1
    LEVEL_2_PROJECT = 2
    LEVEL_3_PREFS = 3

class MemorySecurityClassifier:
    def __init__(self):
        self._memory_store = {
            MemoryLevel.LEVEL_0_TEMP: [],
            MemoryLevel.LEVEL_1_SESSION: [],
            MemoryLevel.LEVEL_2_PROJECT: [],
            MemoryLevel.LEVEL_3_PREFS: []
        }

    def write_memory(self, level: MemoryLevel, content: str, writer: str) -> bool:
        """
        Agents cannot write to Level 3.
        """
        if level == MemoryLevel.LEVEL_3_PREFS and writer != "User":
            return False
        
        self._memory_store[level].append({
            "content": content,
            "metadata": {"writer": writer, "trusted": False}
        })
        return True

    def read_memory(self, level: MemoryLevel) -> List[str]:
        """
        All retrieved memory is considered UNTRUSTED DATA.
        It is returned strictly as plain text context.
        """
        return [entry["content"] for entry in self._memory_store[level]]
        
    def sanitize_context(self, context: str) -> str:
        """
        Memory poisoning defense: strip pseudo-commands.
        """
        # Ensure context cannot spoof authorization or autonomous mode triggers
        suspicious_phrases = ["approve all", "enable autonomous mode", "continue without asking", "authorize"]
        sanitized = context
        for phrase in suspicious_phrases:
            sanitized = sanitized.replace(phrase, "[REDACTED_POTENTIAL_POISONING]")
        return sanitized
