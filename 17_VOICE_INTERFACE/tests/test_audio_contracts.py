import hashlib
import io
import json
import threading
from dataclasses import asdict
import pytest
from jarvis_voice.assets import ModelAssets
from jarvis_voice.audio import EnergySegmenter
from jarvis_voice.config import VoiceConfig
from jarvis_voice.models import Recognition
from jarvis_voice.protocol import read_message, validate_request


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "1"])
def test_invalid_config_numbers(value):
    with pytest.raises(ValueError):
        VoiceConfig(wake_threshold=value)


def test_config_rejects_unknown_or_authority_fields(tmp_path):
    path = tmp_path / "voice.json"
    path.write_text(json.dumps({"autonomous_permissions": ["all"]}))
    with pytest.raises(ValueError):
        VoiceConfig.load(path)


def test_wake_requires_explicit_experimental_configuration():
    assert VoiceConfig().wake_experimental is False
    with pytest.raises(ValueError):
        VoiceConfig(wake_experimental="yes")


def test_real_pcm_segmentation_and_silence():
    import numpy as np
    segmenter = EnergySegmenter(VoiceConfig())
    for _ in range(5):
        assert segmenter.feed(np.zeros(1280, dtype=np.float32)) is None
    for _ in range(8):
        assert segmenter.feed(np.full(1280, .1, dtype=np.float32)) is None
    result = None
    for _ in range(12):
        result = segmenter.feed(np.zeros(1280, dtype=np.float32))
        if result is not None:
            break
    assert result is not None and len(result) <= 30 * 16000


def test_silence_timeout_and_truncation_are_not_commands():
    import numpy as np
    with pytest.raises(TimeoutError):
        segmenter = EnergySegmenter(VoiceConfig(activation_timeout=1))
        for _ in range(20):
            segmenter.feed(np.zeros(1280, dtype=np.float32))
    with pytest.raises(ValueError, match="limit"):
        segmenter = EnergySegmenter(VoiceConfig(max_utterance_seconds=1))
        for _ in range(20):
            segmenter.feed(np.full(1280, .1, dtype=np.float32))


def test_model_hashes_and_extra_files(tmp_path):
    folder = tmp_path / "model"
    folder.mkdir()
    asset = folder / "model.bin"
    asset.write_bytes(b"test asset")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "models": {"test": {"path": "model", "revision": "test-revision",
        "license": "test-only", "release_decision": "test-only", "files": {"model.bin": hashlib.sha256(asset.read_bytes()).hexdigest()}}}}))
    assert ModelAssets(manifest).resolve("test") == folder
    (folder / "unexpected.bin").write_bytes(b"unverified")
    with pytest.raises(ValueError, match="unverified"):
        ModelAssets(manifest).resolve("test")
    (folder / "unexpected.bin").unlink()
    asset.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        ModelAssets(manifest).resolve("test")


@pytest.mark.parametrize("raw", [b'{"version":1,"id":"x"}\n', b'{}\n', b'a' * 65537,
                                b'{"version":1,"id":"' + b'a' * 32 + b'","n":NaN}\n'],
                         ids=["bad-id", "no-version", "oversized", "non-finite"])
def test_malformed_wire_is_rejected(raw):
    with pytest.raises(ValueError):
        read_message(io.BytesIO(raw))


@pytest.mark.parametrize("operation,payload", [("execute", {}), ("speak", {"text": "x", "source": "TEXT"}),
                                             ("listen", {"mode": "always"}), ("cancel", {"request_id": "all"})])
def test_worker_cannot_inject_authority_or_generic_execution(operation, payload):
    with pytest.raises(ValueError):
        validate_request({"version": 1, "id": "a" * 32, "operation": operation, "payload": payload})


def test_transcript_cannot_carry_origin_or_approval():
    wire = asdict(Recognition("check citations", "en", -.1, .01, 1))
    wire["origin"] = "local_control"
    with pytest.raises(ValueError):
        Recognition.from_wire(wire)
