"""Configuration model for the Stone 7 voice layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class VoiceConfig:
    """Runtime options controlling voice input and output."""

    enabled: bool = False
    wake_word: str = "Jarvis"
    language: str = "en"
    provider: str = "local"
    speech_rate: str = "normal"

    def __post_init__(self) -> None:
        if not self.wake_word.strip():
            raise ValueError("voice.wake_word cannot be empty.")
        if not self.language.strip():
            raise ValueError("voice.language cannot be empty.")
        if self.provider not in {"local", "mock"}:
            raise ValueError(
                "Unsupported voice provider. Stone 7 supports 'local' and 'mock'."
            )
        if self.speech_rate not in {"slow", "normal", "fast"}:
            raise ValueError("voice.speech_rate must be slow, normal, or fast.")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "VoiceConfig":
        """Build a validated configuration from the YAML voice section."""

        values = values or {}
        return cls(
            enabled=bool(values.get("enabled", False)),
            wake_word=str(values.get("wake_word", "Jarvis")),
            language=str(values.get("language", "en")),
            provider=str(values.get("provider", "local")).lower(),
            speech_rate=str(values.get("speech_rate", "normal")).lower(),
        )
