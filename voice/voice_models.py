"""Typed transfer models for the Stone 7 voice interface."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


class AudioStatus(str, Enum):
    """Observable outcomes of a speech synthesis request."""

    PENDING = "pending"
    PLAYING = "playing"
    SPOKEN = "spoken"
    STOPPED = "stopped"
    DISABLED = "disabled"
    IGNORED = "ignored"
    ERROR = "error"


@dataclass(frozen=True)
class Transcript:
    """Text and metadata produced by a speech recognizer."""

    text: str
    confidence: float = 1.0
    language: str = "en"
    timestamp: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Transcript confidence must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass(frozen=True)
class VoiceCommand:
    """A normalized command extracted from a recognized utterance."""

    text: str
    timestamp: datetime = field(default_factory=utc_now)
    confidence: float = 1.0
    wake_word_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass(frozen=True)
class VoiceResponse:
    """Text returned by Jarvis and the state of its spoken rendition."""

    text: str
    audio_status: AudioStatus
    command: VoiceCommand | None = None
    kernel_result: Any = field(default=None, repr=False)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["audio_status"] = self.audio_status.value
        if self.command is not None:
            data["command"]["timestamp"] = self.command.timestamp.isoformat()
        return data
