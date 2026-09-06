"""One-shot, privacy-preserving acceptance check for the PTT path."""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from conversation_core.chat_manager import ChatManager

from .backend import WorkspaceBackend
from .models import Recognition
from .session import VoiceSession


@dataclass
class PttAcceptanceResult:
    """Authorized hardware-test metadata only; raw audio is never retained."""
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    ok: bool = False
    mode: str = "ptt"
    devices: dict = field(default_factory=dict)
    expected_text: str | None = None
    recognized_text: str | None = None
    latency_ms: int | None = None
    command_result: str | None = None
    tts_playback_heard: bool | None = None
    steps: list = field(default_factory=list)
    failure: str | None = None

    def step(self, name, status, **details):
        self.steps.append({"name": name, "status": status, **details})

    def wire(self):
        return {"version": 1, "kind": "stone_26_5_ptt_acceptance",
                "selected_input_device_ids": [item["id"] for item in self.devices.get("inputs", [])],
                "selected_output_device_ids": [item["id"] for item in self.devices.get("outputs", [])],
                "expected_text": self.expected_text, "recognized_text": self.recognized_text,
                "latency_ms": self.latency_ms, "command_result": self.command_result,
                "tts_playback_heard": self.tts_playback_heard, "pass": self.ok}


def configured_devices(devices, config):
    """Return only configured-device capability metadata, never recorded audio."""
    if not isinstance(devices, list) or not all(isinstance(item, dict) for item in devices):
        raise ValueError("Worker returned invalid device list")

    def select(selector, capability):
        matches = devices if selector is None else [item for item in devices
                                                    if item.get("id") == selector or item.get("name") == selector]
        return [{"id": item.get("id"), capability: item.get(capability)}
                for item in matches if isinstance(item.get(capability), int) and item[capability] > 0]

    inputs, outputs = select(config.input_device, "inputs"), select(config.output_device, "outputs")
    return {"inputs": inputs, "outputs": outputs,
            "ready": bool(inputs and outputs)}


def write_result(path, result):
    """Atomically persist the non-audio result for a bounded local test run."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result.wire(), indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def run_ptt_acceptance(*, worker, config, thesis_root, result_path, timeout=60, chat_factory=ChatManager,
                       platform_root=None, expected_text="check thesis citations"):
    """Run exactly one PTT turn and always stop/close the audio worker.

    The transcript is passed directly to the existing read-only route but is not
    retained unless the caller explicitly supplies it as the authorized expected
    test phrase. Wake mode, approval workflows, and persistent audit output are
    deliberately outside this acceptance check.
    """
    if not 1 <= timeout <= 60:
        raise ValueError("PTT acceptance timeout must be between 1 and 60 seconds")
    if not isinstance(expected_text, str) or not expected_text or len(expected_text) > 200:
        raise ValueError("Expected hardware-test text is invalid")
    result = PttAcceptanceResult(expected_text=expected_text)
    session = None
    try:
        devices = worker.request("devices", timeout=min(timeout, 10))
        result.devices = configured_devices(devices, config)
        result.step("devices", "completed", ready=result.devices["ready"])
        if not result.devices["ready"]:
            raise RuntimeError("Configured input or output device is unavailable")

        backend = WorkspaceBackend(thesis_root, platform_root=platform_root)
        # No ledger path is supplied: this harness does not create an audit artifact.
        chat = chat_factory(backend=backend)
        session = VoiceSession(chat, worker, language=config.language)
        session.enable()
        capture_started = time.monotonic()
        reply = session.listen("ptt", timeout=timeout)
        result.latency_ms = round((time.monotonic() - capture_started) * 1000)
        transcripts = [event["text"] for event in session.events if event["kind"] == "transcript"]
        result.recognized_text = transcripts[-1] if transcripts else None
        result.command_result = reply.status
        result.step("capture_transcript", "completed" if reply.status != "error" else "failed",
                    reply_status=reply.status)
        if reply.status != "completed":
            raise RuntimeError("PTT transcript did not produce a completed read-only inspection")
        result.step("safe_inspection", "completed", reply_status=reply.status,
                    read_only=bool(reply.data and reply.data.get("read_only")))
        if not reply.data or not reply.data.get("read_only"):
            raise RuntimeError("PTT request did not return a read-only inspection")

        spoken = session.speak(reply, timeout=timeout)
        result.step("speak", "completed" if spoken else "failed")
        if not spoken:
            raise RuntimeError("Speech playback did not complete")
        result.ok = True
    except (OSError, ValueError, RuntimeError, PermissionError) as exc:
        result.failure = f"{type(exc).__name__}: {str(exc)[:300]}"
        result.step("failure", "failed", error_type=type(exc).__name__)
    finally:
        try:
            if session is not None:
                session.interrupt()
                result.step("stop", "completed")
                session.close()
            else:
                worker.stop()
                result.step("stop", "completed")
        except Exception as exc:  # cleanup must be visible and must not conceal the test result
            result.ok = False
            result.failure = result.failure or f"CleanupError: {str(exc)[:300]}"
            result.step("stop", "failed", error_type=type(exc).__name__)
        result.finished_at = time.time()
        write_result(result_path, result)
    return result
