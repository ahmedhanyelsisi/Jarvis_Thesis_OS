"""Central controller connecting voice I/O to the existing Jarvis kernel."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Protocol

from .config import VoiceConfig
from .speech_to_text import (
    LocalSpeechRecognizer,
    MockSpeechRecognizer,
    SpeechRecognizer,
)
from .text_to_speech import (
    LocalSpeechSynthesizer,
    MockSpeechSynthesizer,
    SpeechSynthesizer,
)
from .voice_models import AudioStatus, Transcript, VoiceCommand, VoiceResponse


class JarvisKernel(Protocol):
    """The unchanged kernel operations consumed by the voice adapter."""

    def process_request(self, request: str) -> Any: ...

    def process_workflow(self, request: str, evaluate: bool = True) -> Any: ...


class VoiceManager:
    """Coordinate wake-word detection, recognition, Jarvis, and synthesis."""

    def __init__(
        self,
        jarvis: JarvisKernel,
        recognizer: SpeechRecognizer | None = None,
        synthesizer: SpeechSynthesizer | None = None,
        config: VoiceConfig | Mapping[str, Any] | None = None,
    ) -> None:
        self.jarvis = jarvis
        self.config = (
            config if isinstance(config, VoiceConfig) else VoiceConfig.from_mapping(config)
        )
        self.recognizer = recognizer or self._build_recognizer()
        self.synthesizer = synthesizer or self._build_synthesizer()
        self.last_command: VoiceCommand | None = None
        self.last_response: VoiceResponse | None = None
        self.last_error: Exception | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        """Whether the background listening loop is active."""

        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """Start a non-blocking microphone loop when voice is enabled."""

        if not self.config.enabled:
            return False
        if self.running:
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_loop,
            name="jarvis-voice-listener",
            daemon=True,
        )
        self._thread.start()
        return True

    def process_voice_command(
        self,
        audio: Any = None,
        *,
        workflow: bool = False,
        evaluate: bool = True,
    ) -> VoiceResponse:
        """Process one utterance through the existing Jarvis API."""

        if not self.config.enabled:
            return self._remember_response(
                VoiceResponse(
                    text="Voice interaction is disabled.",
                    audio_status=AudioStatus.DISABLED,
                )
            )

        captured = self.recognizer.listen() if audio is None else audio
        transcript = self.recognizer.transcribe(captured)
        command_text = self.extract_command(transcript.text)
        command = VoiceCommand(
            text=command_text or "",
            timestamp=transcript.timestamp,
            confidence=transcript.confidence,
            wake_word_detected=command_text is not None,
        )
        self.last_command = command

        if command_text is None:
            return self._remember_response(
                VoiceResponse(
                    text="",
                    audio_status=AudioStatus.IGNORED,
                    command=command,
                )
            )

        if not command_text:
            response_text = "I am listening."
            return self._speak_response(response_text, command=command)

        if workflow:
            kernel_result = self.jarvis.process_workflow(
                command_text,
                evaluate=evaluate,
            )
        else:
            kernel_result = self.jarvis.process_request(command_text)

        response_text = self._render_response(kernel_result)
        return self._speak_response(
            response_text,
            command=command,
            kernel_result=kernel_result,
        )

    def detect_wake_word(self, text: str) -> bool:
        """Return true only when the configured wake word starts the utterance."""

        return self.extract_command(text) is not None

    def extract_command(self, text: str) -> str | None:
        """Remove a case-insensitive leading wake word from an utterance."""

        wake_word = re.escape(self.config.wake_word.strip())
        match = re.match(
            rf"^\s*{wake_word}(?=\W|$)[\s,;:!?.-]*(.*)$",
            str(text),
            flags=re.IGNORECASE,
        )
        return match.group(1).strip() if match else None

    def shutdown(self) -> None:
        """Stop listening and any speech currently in progress."""

        self._stop_event.set()
        self.synthesizer.stop()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None

    def _listen_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.process_voice_command()
            except EOFError:
                break
            except Exception as exc:  # microphone/provider errors are observable
                self.last_error = exc
                break

    def _build_recognizer(self) -> SpeechRecognizer:
        if self.config.provider == "mock":
            return MockSpeechRecognizer(language=self.config.language)
        return LocalSpeechRecognizer(language=self.config.language)

    def _build_synthesizer(self) -> SpeechSynthesizer:
        if self.config.provider == "mock":
            return MockSpeechSynthesizer()
        return LocalSpeechSynthesizer(speech_rate=self.config.speech_rate)

    def _speak_response(
        self,
        text: str,
        *,
        command: VoiceCommand,
        kernel_result: Any = None,
    ) -> VoiceResponse:
        try:
            status = self.synthesizer.speak(text)
            response = VoiceResponse(
                text=text,
                audio_status=status,
                command=command,
                kernel_result=kernel_result,
            )
        except Exception as exc:
            response = VoiceResponse(
                text=text,
                audio_status=AudioStatus.ERROR,
                command=command,
                kernel_result=kernel_result,
                error=str(exc),
            )
        return self._remember_response(response)

    def _remember_response(self, response: VoiceResponse) -> VoiceResponse:
        self.last_response = response
        return response

    @classmethod
    def _render_response(cls, result: Any) -> str:
        """Produce readable speech text while preserving the kernel result."""

        if result is None:
            return "The request completed without a response."
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if result.get("final_response") is not None:
                return cls._render_response(result["final_response"])
            nested = result.get("result")
            if isinstance(nested, str):
                return nested
            if result.get("message"):
                return str(result["message"])
        if is_dataclass(result) and not isinstance(result, type):
            result = asdict(result)
        try:
            return json.dumps(result, default=str, sort_keys=True)
        except (TypeError, ValueError):
            return str(result)
