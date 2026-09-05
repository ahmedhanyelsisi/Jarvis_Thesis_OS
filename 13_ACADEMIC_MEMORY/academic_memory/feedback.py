import uuid
from typing import List, Optional
from .models import FeedbackRecord, LearningPattern
from .governance import MemoryGovernance
from .memory_store import MemoryStore

class FeedbackEngine:
    """Processes human feedback into structured learning patterns."""
    
    def __init__(self, store: MemoryStore):
        self._store = store

    def store_feedback(self, session_id: str, context: str, text: str) -> FeedbackRecord:
        clean_context = MemoryGovernance.sanitize_text(context)
        clean_text = MemoryGovernance.sanitize_text(text)
        
        record = FeedbackRecord(
            feedback_id=str(uuid.uuid4()),
            session_id=session_id,
            context=clean_context,
            feedback_text=clean_text,
            timestamp="now"
        )
        
        # Save as json list for simplicity
        filename = f"feedback_{session_id}.json"
        existing = self._store.load_json(filename) or {"records": []}
        
        existing["records"].append({
            "feedback_id": record.feedback_id,
            "session_id": record.session_id,
            "context": record.context,
            "feedback_text": record.feedback_text
        })
        
        self._store.save_json(filename, existing)
        return record

    def get_learning_pattern(self, session_id: str, topic: str) -> LearningPattern:
        """Synthesizes a pattern from stored feedback based on topic."""
        # Simple placeholder for LLM semantic grouping.
        # Required confidence scoring logic:
        filename = f"feedback_{session_id}.json"
        data = self._store.load_json(filename)
        records = data.get("records", []) if data else []
        
        # Calculate confidence based on frequency
        relevant = [r for r in records if topic.lower() in r["context"].lower() or topic.lower() in r["feedback_text"].lower()]
        
        if not relevant:
            confidence = 0.0
            desc = f"No pattern found for {topic}."
        else:
            confidence = min(1.0, len(relevant) * 0.2)
            desc = f"Aggregated {len(relevant)} feedback points regarding {topic}."
            
        return LearningPattern(
            pattern_id=str(uuid.uuid4()),
            topic=topic,
            pattern_description=desc,
            confidence=confidence
        )
