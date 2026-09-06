"""Strict, opt-in configuration separate from frozen Jarvis configuration."""
import json
import math
from dataclasses import dataclass, fields, asdict
from pathlib import Path


@dataclass(frozen=True)
class VoiceConfig:
    language: str = "en"
    input_device: int | str | None = None
    output_device: int | str | None = None
    device_sample_rate: int = 16000
    wake_threshold: float = 0.6
    vad_rms: float = 0.012
    silence_seconds: float = 0.8
    activation_timeout: float = 10.0
    max_utterance_seconds: float = 30.0
    wake_timeout: float = 60.0
    wake_experimental: bool = False
    model_manifest: str = "model_manifest.json"
    whisper_model: str = "whisper"
    piper_model: str = "piper"
    wake_model: str = "wake"
    melspectrogram_model: str = "melspectrogram"
    embedding_model: str = "embedding"
    tts_provider: str = "piper"
    speech_rate: float = 1.0
    cpu_threads: int = 4

    def __post_init__(self):
        if self.language != "en":
            raise ValueError("This release validates English only")
        if self.tts_provider not in ("piper", "windows"):
            raise ValueError("Unknown synthesis provider")
        if type(self.wake_experimental) is not bool:
            raise ValueError("Invalid wake_experimental setting")
        for value in (self.input_device, self.output_device):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (str, int))):
                raise ValueError("Invalid device selector")
        if type(self.device_sample_rate) is not int or self.device_sample_rate not in (16000, 32000, 44100, 48000):
            raise ValueError("Unsupported device sample rate")
        if type(self.cpu_threads) is not int or not 1 <= self.cpu_threads <= 16:
            raise ValueError("Invalid CPU thread limit")
        for key, low, high in (("wake_threshold", .1, 1), ("vad_rms", .001, .5),
                               ("silence_seconds", .2, 3), ("activation_timeout", 1, 15),
                               ("max_utterance_seconds", 1, 30), ("wake_timeout", 1, 120),
                               ("speech_rate", .5, 2)):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"Invalid {key}")

    @classmethod
    def load(cls, path):
        path = Path(path).resolve(strict=True)
        if path.stat().st_size > 16384:
            raise ValueError("Configuration exceeds size limit")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) - {f.name for f in fields(cls)}:
            raise ValueError("Unknown configuration fields")
        data["model_manifest"] = str((path.parent / data.get("model_manifest", "model_manifest.json")).resolve())
        return cls(**data)

    def to_dict(self):
        return asdict(self)
