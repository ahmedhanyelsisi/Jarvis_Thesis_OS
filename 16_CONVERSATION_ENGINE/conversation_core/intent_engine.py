import json
import re
from typing import Dict, Any, Optional, Tuple

class IntentEngine:
    def __init__(self):
        self.supported_intents = [
            "improve_chapter",
            "analyze_literature",
            "find_papers",
            "prepare_submission",
            "approve_all",
            "enable_autonomous_mode",
            "continue_without_asking",
            "approve_all_thesis_operations"
        ]

    def _semantic_understanding_layer(self, user_input: str) -> Dict[str, Any]:
        """
        Simulates an LLM or semantic parser extracting raw intent and entities.
        """
        user_input_lower = user_input.lower()
        
        # Pattern matching for autonomous mode
        if user_input_lower in ["jarvis approve all", "approve all", "enable autonomous mode", "continue without asking", "approve all thesis operations"]:
            return {"task": "enable_autonomous_mode", "confidence": 1.0}

        # Heuristic matching for thesis tasks
        if "improve" in user_input_lower and "chapter" in user_input_lower:
            target = "chapter_unknown"
            if "methodology" in user_input_lower or "chapter 3" in user_input_lower:
                target = "chapter_3_methodology"
            return {"task": "improve_chapter", "target": target, "confidence": 0.9}
            
        if "analyze" in user_input_lower and "literature" in user_input_lower:
            return {"task": "analyze_literature", "target": "literature_review", "confidence": 0.85}
            
        if "find" in user_input_lower and "papers" in user_input_lower:
            topic = "topic_unknown"
            if "transformers" in user_input_lower:
                topic = "transformers"
            return {"task": "find_papers", "target": topic, "confidence": 0.9}
            
        if "prepare" in user_input_lower and "submission" in user_input_lower:
            return {"task": "prepare_submission", "target": "final_thesis", "confidence": 0.95}

        # Fallback for ambiguous inputs
        return {"task": "unknown", "confidence": 0.0}

    def _structured_intent_validation(self, raw_intent: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates the extracted intent against supported tasks and required arguments.
        """
        task = raw_intent.get("task")
        if task not in self.supported_intents:
            return False, "Unsupported or unrecognized intent."
            
        if task in ["improve_chapter", "analyze_literature", "find_papers"]:
            if "target" not in raw_intent or "unknown" in raw_intent.get("target", ""):
                return False, f"Missing specific target for task: {task}"
                
        return True, None

    def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Main entrypoint. Existing gateway authority remains final (downstream authorization).
        """
        raw_intent = self._semantic_understanding_layer(user_input)
        is_valid, validation_msg = self._structured_intent_validation(raw_intent)
        
        if not is_valid:
            raw_intent["status"] = "ambiguous"
            raw_intent["clarification_needed"] = validation_msg
        else:
            raw_intent["status"] = "resolved"
            
        return raw_intent
