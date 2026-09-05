from typing import Dict, Any, List
from security.memory_security_classifier import MemorySecurityClassifier, MemoryLevel

class ContextManager:
    def __init__(self):
        self.memory_classifier = MemorySecurityClassifier()
        self.pending_intent: Dict[str, Any] = {}
        
    def add_interaction(self, role: str, content: str):
        # Level 0 for temporary conversation
        self.memory_classifier.write_memory(MemoryLevel.LEVEL_0_TEMP, content, role)
        
    def get_conversation_history(self) -> List[str]:
        raw_history = self.memory_classifier.read_memory(MemoryLevel.LEVEL_0_TEMP)
        # Apply poisoning defense to any retrieved context
        return [self.memory_classifier.sanitize_context(msg) for msg in raw_history]
        
    def requires_clarification(self, intent: Dict[str, Any]) -> bool:
        if intent.get("status") == "ambiguous":
            return True
        return False
        
    def generate_clarification_prompt(self, intent: Dict[str, Any]) -> str:
        self.pending_intent = intent
        msg = intent.get("clarification_needed", "Could you please clarify your request?")
        return f"Clarification needed: {msg}"
        
    def resolve_pending_intent(self, user_clarification: str) -> Dict[str, Any]:
        """
        Merge user clarification with pending intent.
        """
        # Very simple heuristic for simulation
        if not self.pending_intent:
            return {}
            
        task = self.pending_intent.get("task")
        if task in ["improve_chapter", "analyze_literature", "find_papers"]:
            # Assume the user provided the missing target
            self.pending_intent["target"] = user_clarification
            self.pending_intent["status"] = "resolved"
            self.pending_intent["clarification_needed"] = None
            
        resolved = dict(self.pending_intent)
        self.pending_intent = {}
        return resolved
