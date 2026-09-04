"""Speech-synthesis providers for the Stone 7 voice layer."""

from __future__ import annotations

import base64
import platform
import shutil
import subprocess
import threading
from abc import ABC, abstractmethod

from .voice_models import AudioStatus


class SpeechSynthesisError(RuntimeError):
    """Raised when local text-to-speech cannot complete."""


class SpeechSynthesizer(ABC):
    """Provider-neutral text-to-speech contract."""

    @abstractmethod
    def speak(self, text: str) -> AudioStatus:
        """Speak text and return its terminal audio state."""

    @abstractmethod
    def stop(self) -> None:
        """Stop current speech, if any."""


class MockSpeechSynthesizer(SpeechSynthesizer):
    """Synthesizer test double that records text instead of playing audio."""

    def __init__(self) -> None:
        self.spoken_texts: list[str] = []
        self.stopped = False

    @property
    def last_spoken(self) -> str | None:
        return self.spoken_texts[-1] if self.spoken_texts else None

    def speak(self, text: str) -> AudioStatus:
        self.spoken_texts.append(str(text))
        self.stopped = False
        return AudioStatus.SPOKEN

    def stop(self) -> None:
        self.stopped = True


class LocalSpeechSynthesizer(SpeechSynthesizer):
    """Windows text-to-speech backed by the built-in ``System.Speech`` API."""

    _SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speaker.Rate = __RATE__
    $text = [System.Text.Encoding]::UTF8.GetString(
        [System.Convert]::FromBase64String('__TEXT_BASE64__')
    )
    $speaker.Speak($text)
} finally {
    $speaker.Dispose()
}
"""
    _RATES = {"slow": -3, "normal": 0, "fast": 3}

    def __init__(self, speech_rate: str = "normal") -> None:
        if speech_rate not in self._RATES:
            raise ValueError("speech_rate must be slow, normal, or fast.")
        self.speech_rate = speech_rate
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    @staticmethod
    def _powershell() -> str:
        executable = shutil.which("powershell") or shutil.which("powershell.exe")
        if platform.system() != "Windows" or executable is None:
            raise SpeechSynthesisError(
                "The local Stone 7 synthesizer requires Windows PowerShell."
            )
        return executable

    def speak(self, text: str) -> AudioStatus:
        if not str(text).strip():
            return AudioStatus.SPOKEN
        self.stop()
        process: subprocess.Popen[str] | None = None
        try:
            encoded_text = base64.b64encode(
                str(text).encode("utf-8")
            ).decode("ascii")
            script = self._SCRIPT.replace(
                "__RATE__",
                str(self._RATES[self.speech_rate]),
            ).replace("__TEXT_BASE64__", encoded_text)
            encoded_script = base64.b64encode(
                script.encode("utf-16-le")
            ).decode("ascii")
            with self._lock:
                self._process = subprocess.Popen(
                    [
                        self._powershell(),
                        "-NoProfile",
                        "-NonInteractive",
                        "-EncodedCommand",
                        encoded_script,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                process = self._process
            _, stderr = process.communicate()
            if process.returncode:
                raise SpeechSynthesisError(
                    f"Local speech synthesis failed: {stderr.strip()}"
                )
            return AudioStatus.SPOKEN
        except OSError as exc:
            raise SpeechSynthesisError(
                f"Local speech synthesis failed: {exc}"
            ) from exc
        finally:
            with self._lock:
                if process is not None and self._process is process:
                    self._process = None

    def stop(self) -> None:
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
