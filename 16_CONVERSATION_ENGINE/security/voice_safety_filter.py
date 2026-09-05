from enum import Enum
from typing import Dict, Any

class InputSource(Enum):
    TEXT = "TEXT"
    VOICE_CONFIRMED = "VOICE_CONFIRMED"
    VOICE_UNCONFIRMED = "VOICE_UNCONFIRMED"

class VoiceSafetyFilter:
    def __init__(self):
        self.confidence_threshold = 0.85
        
    def filter_input(self, text: str, source: InputSource, confidence: float = 1.0, has_wake_word: bool = True) -> Dict[str, Any]:
        """
        Prepare interfaces for future voice input. 
        Background audio cannot authorize actions.
        """
        if source == InputSource.TEXT:
            return {"safe": True, "text": text, "source": source}
            
        if not has_wake_word:
            return {"safe": False, "reason": "Missing wake word"}
            
        if confidence < self.confidence_threshold:
            # Low confidence input could be background speech
            # Especially dangerous if it's an authorization command
            dangerous_commands = ["approve all", "enable autonomous mode", "yes", "approve"]
            if any(cmd in text.lower() for cmd in dangerous_commands):
                return {"safe": False, "reason": "Low confidence authorization command rejected"}
            
            # For non-dangerous commands, maybe it's just unconfirmed
            return {"safe": True, "text": text, "source": InputSource.VOICE_UNCONFIRMED}
            
        return {"safe": True, "text": text, "source": InputSource.VOICE_CONFIRMED}
