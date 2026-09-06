"""Bounded wire and session data; no permissions are carried by transcripts."""
import math
import time
from dataclasses import dataclass
from enum import Enum


class SessionState(str, Enum):
    STOPPED = "stopped"
    MUTED = "muted"
    READY = "ready"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    CLARIFYING = "clarifying"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    EXECUTING = "executing"
    ERROR = "error"


class Quality(str, Enum):
    HIGH = "high"
    UNCERTAIN = "uncertain"
    REJECT = "reject"


@dataclass(frozen=True)
class Recognition:
    text: str
    language: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None
    final: bool = True
    truncated: bool = False

    @classmethod
    def from_wire(cls, value):
        if not isinstance(value, dict) or set(value) != set(cls.__dataclass_fields__):
            raise ValueError("Invalid transcript fields")
        if not isinstance(value["text"], str) or len(value["text"]) > 4096:
            raise ValueError("Invalid transcript text")
        if not isinstance(value["language"], str) or len(value["language"]) > 16:
            raise ValueError("Invalid language")
        if type(value["final"]) is not bool or type(value["truncated"]) is not bool:
            raise ValueError("Invalid transcript flags")
        return cls(**value)


def assess_quality(recognition, language="en"):
    if (not recognition.final or recognition.truncated or not recognition.text.strip()
            or len(recognition.text) > 4096 or recognition.language != language):
        return Quality.REJECT
    values = (recognition.avg_logprob, recognition.no_speech_prob, recognition.compression_ratio)
    if any(value is None for value in values):
        return Quality.UNCERTAIN
    if any(isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) for value in values):
        return Quality.REJECT
    logprob, silence, ratio = values
    if not -100 <= logprob <= 0 or not 0 <= silence <= 1 or not 0 <= ratio <= 100:
        return Quality.REJECT
    if silence >= 0.6 or ratio > 2.4 or logprob < -1.0:
        return Quality.UNCERTAIN
    return Quality.HIGH
