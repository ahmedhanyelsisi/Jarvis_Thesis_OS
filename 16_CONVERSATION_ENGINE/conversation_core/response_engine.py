class ResponseEngine:
    def __init__(self):
        pass
        
    def generate_chat_response(self, text: str) -> str:
        """
        Standard text response for chat interface.
        """
        return f"JARVIS: {text}"
        
    def generate_voice_response(self, text: str, ssml_tags: str = "") -> dict:
        """
        Future compatibility for text-to-speech.
        """
        return {
            "text": text,
            "ssml": f"<speak>{ssml_tags}{text}</speak>"
        }
        
    def stream_response(self, text: str):
        """
        Yields chunks of text for streaming interfaces.
        """
        for word in text.split():
            yield word + " "
            
    def emit_ui_state(self, state: str) -> dict:
        """
        Emits UI animation states (e.g., thinking, speaking, executing).
        """
        valid_states = ["idle", "thinking", "speaking", "executing", "waiting_for_approval"]
        if state not in valid_states:
            state = "idle"
        return {"ui_animation_state": state}
