"""Stone 7 voice-layer unit and kernel-integration tests."""

from pathlib import Path

import voice
from voice import (
    AudioStatus,
    MockSpeechRecognizer,
    MockSpeechSynthesizer,
    Transcript,
    VoiceManager,
)

from jarvis import Jarvis


class RecordingKernel:
    def __init__(self) -> None:
        self.requests: list[str] = []

    def process_request(self, request: str) -> str:
        self.requests.append(request)
        return f"Completed: {request}"

    def process_workflow(self, request: str, evaluate: bool = True) -> dict:
        self.requests.append(request)
        return {"final_response": f"Workflow completed: {request}"}


def _manager(
    utterance: str,
    *,
    enabled: bool = True,
    wake_word: str = "Jarvis",
) -> tuple[VoiceManager, RecordingKernel, MockSpeechSynthesizer]:
    kernel = RecordingKernel()
    synthesizer = MockSpeechSynthesizer()
    manager = VoiceManager(
        kernel,
        recognizer=MockSpeechRecognizer(utterance),
        synthesizer=synthesizer,
        config={
            "enabled": enabled,
            "wake_word": wake_word,
            "language": "en",
            "provider": "mock",
            "speech_rate": "normal",
        },
    )
    return manager, kernel, synthesizer


def test_voice_package_imports_successfully():
    assert voice.VoiceManager is VoiceManager
    assert voice.SpeechRecognizer is not None
    assert voice.SpeechSynthesizer is not None


def test_speech_recognition_mock_works():
    recognizer = MockSpeechRecognizer(
        Transcript(text="Jarvis summarize chapter two", confidence=0.91)
    )

    transcript = recognizer.transcribe(recognizer.listen())

    assert transcript.text == "Jarvis summarize chapter two"
    assert transcript.confidence == 0.91


def test_text_to_speech_mock_works():
    synthesizer = MockSpeechSynthesizer()

    status = synthesizer.speak("Draft ready")
    synthesizer.stop()

    assert status == AudioStatus.SPOKEN
    assert synthesizer.last_spoken == "Draft ready"
    assert synthesizer.stopped is True


def test_wake_word_detection_accepts_prefixed_commands_and_ignores_others():
    manager, _, _ = _manager("unused")

    assert manager.detect_wake_word("Jarvis write my literature review")
    assert manager.extract_command("jarvis, summarize chapter two") == (
        "summarize chapter two"
    )
    assert not manager.detect_wake_word("write my literature review")


def test_voice_disabled_mode_does_not_capture_or_call_kernel():
    manager, kernel, synthesizer = _manager(
        "Jarvis write my literature review",
        enabled=False,
    )

    response = manager.process_voice_command()

    assert response.audio_status == AudioStatus.DISABLED
    assert kernel.requests == []
    assert synthesizer.spoken_texts == []
    assert manager.start() is False


def test_command_without_wake_word_is_ignored():
    manager, kernel, synthesizer = _manager("write my literature review")

    response = manager.process_voice_command()

    assert response.audio_status == AudioStatus.IGNORED
    assert response.command is not None
    assert response.command.wake_word_detected is False
    assert kernel.requests == []
    assert synthesizer.spoken_texts == []


def test_voice_command_reaches_existing_jarvis_kernel_method():
    manager, kernel, synthesizer = _manager(
        "Jarvis write my literature review"
    )

    response = manager.process_voice_command()

    assert kernel.requests == ["write my literature review"]
    assert response.text == "Completed: write my literature review"
    assert response.audio_status == AudioStatus.SPOKEN
    assert synthesizer.last_spoken == response.text


def test_jarvis_voice_integration_is_optional_and_uses_runtime_config(
    tmp_path: Path,
):
    config = {
        "knowledge": {"enabled": False},
        "memory": {"enabled": False},
        "reasoning": {
            "enabled": True,
            "memory_path": str(tmp_path / "reasoning.json"),
        },
        "planner": {"enabled": True},
        "evaluation": {"enabled": False},
        "voice": {
            "enabled": True,
            "wake_word": "Computer",
            "language": "en",
            "provider": "mock",
            "speech_rate": "fast",
        },
    }
    jarvis = Jarvis(config=config)
    assert jarvis.voice_manager is not None
    assert jarvis.voice_manager.config.wake_word == "Computer"
    jarvis.voice_manager.recognizer.queue("Computer create a diagram")

    response = jarvis.process_voice_command()

    assert response.command is not None
    assert response.command.text == "create a diagram"
    assert response.kernel_result["agent"] == "diagram_agent"
    assert response.audio_status == AudioStatus.SPOKEN
    jarvis.close()
