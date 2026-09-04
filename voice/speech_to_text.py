"""Local-first speech-recognition abstractions and test doubles."""

from __future__ import annotations

import base64
import json
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterable
from typing import Any

from .voice_models import Transcript


class SpeechRecognitionError(RuntimeError):
    """Raised when local audio capture or recognition cannot complete."""


class SpeechRecognizer(ABC):
    """Provider-neutral speech-to-text contract."""

    @abstractmethod
    def listen(self) -> Any:
        """Capture and return one provider-specific audio payload."""

    @abstractmethod
    def transcribe(self, audio: Any) -> Transcript:
        """Convert an audio payload into a typed transcript."""


class MockSpeechRecognizer(SpeechRecognizer):
    """Deterministic recognizer used by tests and offline development."""

    def __init__(
        self,
        transcripts: str | Transcript | Iterable[str | Transcript] | None = None,
        *,
        confidence: float = 1.0,
        language: str = "en",
    ) -> None:
        if transcripts is None:
            initial: list[str | Transcript] = []
        elif isinstance(transcripts, (str, Transcript)):
            initial = [transcripts]
        else:
            initial = list(transcripts)
        self._items = deque(initial)
        self.confidence = confidence
        self.language = language

    def queue(self, transcript: str | Transcript) -> None:
        """Append a transcript returned by a future ``listen`` call."""

        self._items.append(transcript)

    def listen(self) -> str | Transcript:
        if not self._items:
            raise EOFError("The mock speech recognizer has no queued input.")
        return self._items.popleft()

    def transcribe(self, audio: Any) -> Transcript:
        if isinstance(audio, Transcript):
            return audio
        if isinstance(audio, bytes):
            audio = audio.decode("utf-8")
        return Transcript(
            text=str(audio),
            confidence=self.confidence,
            language=self.language,
        )


class LocalSpeechRecognizer(SpeechRecognizer):
    """Use the built-in Windows speech engine without a cloud API.

    The provider deliberately sits behind ``SpeechRecognizer`` so a future local
    Whisper adapter can replace it without changing ``VoiceManager``.
    """

    _SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$installed = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
$requested = [System.Text.Encoding]::UTF8.GetString(
    [System.Convert]::FromBase64String('__LANGUAGE_BASE64__')
)
$recognizerInfo = $installed | Where-Object {
    $_.Culture.Name -eq $requested -or $_.Culture.TwoLetterISOLanguageName -eq $requested
} | Select-Object -First 1
if ($null -eq $recognizerInfo) {
    throw "No installed Windows speech recognizer matches language '$requested'."
}
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine($recognizerInfo)
try {
    $recognizer.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $recognizer.SetInputToDefaultAudioDevice()
    $result = $recognizer.Recognize()
    if ($null -eq $result) { throw "No speech was recognized." }
    @{ text = $result.Text; confidence = $result.Confidence; language = $recognizerInfo.Culture.Name } |
        ConvertTo-Json -Compress
} finally {
    $recognizer.Dispose()
}
"""

    def __init__(self, language: str = "en") -> None:
        self.language = language

    @staticmethod
    def _powershell() -> str:
        executable = shutil.which("powershell") or shutil.which("powershell.exe")
        if platform.system() != "Windows" or executable is None:
            raise SpeechRecognitionError(
                "The local Stone 7 recognizer requires Windows PowerShell and "
                "an installed Windows speech recognition language."
            )
        return executable

    def listen(self) -> dict[str, Any]:
        try:
            language = base64.b64encode(self.language.encode("utf-8")).decode("ascii")
            script = self._SCRIPT.replace("__LANGUAGE_BASE64__", language)
            encoded_script = base64.b64encode(
                script.encode("utf-16-le")
            ).decode("ascii")
            completed = subprocess.run(
                [
                    self._powershell(),
                    "-NoProfile",
                    "-NonInteractive",
                    "-EncodedCommand",
                    encoded_script,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(completed.stdout.strip())
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            detail = getattr(exc, "stderr", None) or str(exc)
            raise SpeechRecognitionError(
                f"Local speech recognition failed: {str(detail).strip()}"
            ) from exc

    def transcribe(self, audio: Any) -> Transcript:
        if isinstance(audio, Transcript):
            return audio
        if isinstance(audio, dict):
            return Transcript(
                text=str(audio.get("text", "")),
                confidence=float(audio.get("confidence", 0.0)),
                language=str(audio.get("language", self.language)),
            )
        raise TypeError("LocalSpeechRecognizer expects audio returned by listen().")
