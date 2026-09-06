"""Provider contract tests complement the separately recorded real-model smoke run."""
import threading
from types import SimpleNamespace
import numpy as np
import pytest
from jarvis_voice.providers import FasterWhisperRecognizer, OpenWakeWordDetector


def recognizer_for(segments):
    recognizer = FasterWhisperRecognizer.__new__(FasterWhisperRecognizer)
    recognizer.language = "en"
    recognizer.model = SimpleNamespace(transcribe=lambda *args, **kwargs: (iter(segments), SimpleNamespace(language="en")))
    return recognizer


def test_all_segment_diagnostics_are_conservative():
    segments = [SimpleNamespace(text="Check", avg_logprob=-.1, no_speech_prob=.01, compression_ratio=1),
                SimpleNamespace(text="citations", avg_logprob=-1.5, no_speech_prob=.8, compression_ratio=3)]
    result = recognizer_for(segments).transcribe(np.zeros(16000), threading.Event())
    assert result.avg_logprob == -1.5
    assert result.no_speech_prob == .8
    assert result.compression_ratio == 3


def test_transcription_cancellation_does_not_return_partial_text():
    cancel = threading.Event()
    cancel.set()
    segment = SimpleNamespace(text="check", avg_logprob=-.1, no_speech_prob=.01, compression_ratio=1)
    with pytest.raises(InterruptedError):
        recognizer_for([segment]).transcribe(np.zeros(16000), cancel)


@pytest.mark.parametrize("score", [float("inf"), float("nan"), -1, 2])
def test_invalid_wake_scores_cannot_activate(score):
    detector = OpenWakeWordDetector.__new__(OpenWakeWordDetector)
    detector.threshold = .6
    detector.model = SimpleNamespace(predict=lambda frame: {"wake": score})
    assert not detector.detected(np.zeros(1280, dtype=np.float32))
