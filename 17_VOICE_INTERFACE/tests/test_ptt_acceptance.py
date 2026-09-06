import json

from jarvis_voice.acceptance import run_ptt_acceptance
from jarvis_voice.config import VoiceConfig
from jarvis_voice.models import Recognition


class AcceptanceWorker:
    def __init__(self, recognition=None, devices=None):
        self.recognition = recognition or Recognition("check thesis citations", "en", -.1, .01, 1)
        self.devices = devices if devices is not None else [
            {"id": 0, "name": "Mic", "inputs": 1, "outputs": 0, "sample_rate": 16000},
            {"id": 1, "name": "Speaker", "inputs": 0, "outputs": 2, "sample_rate": 16000},
        ]
        self.calls, self.event_callback = [], lambda identifier, payload: None
        self.alive = True

    def request(self, operation, payload=None, *, timeout=30, on_started=None):
        self.calls.append((operation, payload, timeout))
        if on_started:
            on_started("a" * 32)
        if operation == "devices":
            return self.devices
        if operation == "listen":
            self.event_callback("a" * 32, {"state": "listening"})
            self.event_callback("a" * 32, {"state": "transcribing"})
            return {**self.recognition.__dict__}
        if operation == "speak":
            self.event_callback("a" * 32, {"state": "speaking"})
            return {"playback": "spoken"}
        raise AssertionError(operation)

    def stop(self):
        self.calls.append(("stop", None, None))
        return True

    def close(self):
        self.calls.append(("close", None, None))
        self.alive = False


def test_ptt_acceptance_records_only_authorized_text_and_no_audio(thesis, tmp_path):
    worker = AcceptanceWorker()
    path = tmp_path / "acceptance.json"
    result = run_ptt_acceptance(worker=worker, config=VoiceConfig(input_device=0, output_device=1),
                                thesis_root=thesis, result_path=path, timeout=5)
    recorded = json.loads(path.read_text())
    assert result.ok and recorded["pass"]
    assert [call[0] for call in worker.calls] == ["devices", "listen", "speak", "stop", "stop", "close"]
    assert [step["name"] for step in result.steps] == ["devices", "capture_transcript", "safe_inspection", "speak", "stop"]
    assert recorded["selected_input_device_ids"] == [0]
    assert recorded["selected_output_device_ids"] == [1]
    assert recorded["expected_text"] == "check thesis citations"
    assert recorded["recognized_text"] == "check thesis citations"
    assert isinstance(recorded["latency_ms"], int)
    assert recorded["command_result"] == "completed"
    assert recorded["tts_playback_heard"] is None
    assert "Read-only inspection" not in json.dumps(recorded)
    assert set(recorded) == {"version", "kind", "selected_input_device_ids", "selected_output_device_ids",
                             "expected_text", "recognized_text", "latency_ms", "command_result",
                             "tts_playback_heard", "pass"}


def test_ptt_acceptance_fails_before_capture_when_configured_device_is_missing(thesis, tmp_path):
    worker = AcceptanceWorker(devices=[])
    result = run_ptt_acceptance(worker=worker, config=VoiceConfig(input_device=0, output_device=1),
                                thesis_root=thesis, result_path=tmp_path / "acceptance.json", timeout=5)
    assert not result.ok
    assert [call[0] for call in worker.calls] == ["devices", "stop"]
    assert result.steps[-1]["name"] == "stop"


def test_ptt_acceptance_rejects_unbounded_timeout(tmp_path, thesis):
    worker = AcceptanceWorker()
    try:
        run_ptt_acceptance(worker=worker, config=VoiceConfig(input_device=0, output_device=1),
                           thesis_root=thesis, result_path=tmp_path / "acceptance.json", timeout=61)
    except ValueError as exc:
        assert "between 1 and 60" in str(exc)
    else:
        raise AssertionError("unbounded timeout accepted")
