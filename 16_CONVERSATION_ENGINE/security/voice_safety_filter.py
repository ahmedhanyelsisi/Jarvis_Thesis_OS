"""Recognition quality never upgrades input provenance or grants authority."""
import math
from enum import Enum


class InputSource(Enum):
    TEXT = "TEXT"
    VOICE_CONFIRMED = "VOICE_CONFIRMED"  # legacy label; not authorization
    VOICE_UNCONFIRMED = "VOICE_UNCONFIRMED"
    AGENT = "AGENT"
    MEMORY = "MEMORY"


class VoiceSafetyFilter:
    confidence_threshold = 0.85

    def filter_input(self, text, source, confidence=None, has_wake_word=False):
        if not isinstance(text, str) or not text.strip() or len(text) > 4096:
            return {"safe": False, "reason": "Invalid or oversized input"}
        if source == InputSource.TEXT:
            return {"safe": True, "text": text.strip(), "source": source}
        if source not in (InputSource.VOICE_CONFIRMED, InputSource.VOICE_UNCONFIRMED):
            return {"safe": False, "reason": "Data-only source cannot issue commands"}
        if not has_wake_word:
            return {"safe": False, "reason": "Missing activation"}
        if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not math.isfinite(confidence) or not 0 <= confidence <= 1):
            return {"safe": False, "reason": "Unknown or invalid recognition quality"}
        if confidence < self.confidence_threshold:
            return {"safe": False, "reason": "Uncertain speech; repeat or use text"}
        return {"safe": True, "text": text.strip(), "source": source}
