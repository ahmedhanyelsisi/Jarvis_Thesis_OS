from typing import Optional

class InterfaceGateway:
    """Unifies Voice and Text input streams into standard commands."""
    
    WAKE_WORD = "hey jarvis"
    
    def __init__(self):
        self._voice_active = False
        self._push_to_talk = False

    def process_text_input(self, text: str) -> str:
        """Processes standard CLI text."""
        return text.strip()

    def process_voice_stream(self, stream_text: str) -> Optional[str]:
        """
        Simulates voice command parsing. Requires WAKE_WORD unless PTT is engaged.
        Returns the command string if triggered, else None.
        """
        stream_lower = stream_text.lower()
        if self._push_to_talk:
            return stream_text.strip()
            
        if stream_lower.startswith(self.WAKE_WORD):
            # Extract everything after the wake word
            return stream_text[len(self.WAKE_WORD):].strip()
            
        # Ignored ambient noise
        return None

    def enable_push_to_talk(self, enabled: bool):
        self._push_to_talk = enabled
