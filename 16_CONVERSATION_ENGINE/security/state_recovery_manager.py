"""Persist only allowlisted preferences; recovery never restores authority."""
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path


class JarvisStateRecovery:
    VERSION = "2.0"
    ALLOWED = frozenset(("language", "voice_id", "speech_rate", "input_device", "output_device"))

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else None
        self._saved = None

    @staticmethod
    def _checksum(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def save_state(self, config, runtime_state):
        safe = {k: v for k, v in runtime_state.items() if k in self.ALLOWED and isinstance(v, (str, int, float)) and not isinstance(v, bool)}
        body = {"version": self.VERSION, "config_checksum": self._checksum(config), "preferences": safe}
        document = dict(body, checksum=self._checksum(body))
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix="voice-preferences-", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(document, stream, allow_nan=False)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        self._saved = document
        return True

    def recover_state(self, config=None):
        safe = {"authorization_mode": "CONTROLLED_MODE"}
        try:
            document = copy.deepcopy(self._saved)
            if self.path:
                if self.path.stat().st_size > 16384:
                    raise ValueError("Oversized preferences")
                document = json.loads(self.path.read_text(encoding="utf-8"))
            if document:
                checksum = document.pop("checksum")
                if checksum != self._checksum(document) or document["version"] != self.VERSION:
                    raise ValueError("Invalid preferences")
                if config is not None and document["config_checksum"] != self._checksum(config):
                    raise ValueError("Configuration changed")
                safe.update({k: v for k, v in document["preferences"].items() if k in self.ALLOWED})
            return {"safe_runtime_state": safe, "recovery_status": "safe"}
        except (OSError, ValueError, TypeError, KeyError):
            return {"safe_runtime_state": {"authorization_mode": "CONTROLLED_MODE"}, "recovery_status": "discarded"}
