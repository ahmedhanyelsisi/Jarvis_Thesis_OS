"""Stdio bootstrap: receives a one-time pairing secret, emits a non-secret descriptor."""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from backend.ipc.backend_server import JarvisIpcBackend


def main() -> int:
    line = sys.stdin.buffer.readline(8192)
    try:
        request = json.loads(line.decode("utf-8"))
        pairing_token = base64.b64decode(request["pairing_token"], validate=True)
    except (KeyError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return 2
    if len(pairing_token) != 32:
        return 2
    state_dir = Path(tempfile.gettempdir()) / "jarvis-thesis-os" / str(os.getpid())
    backend = JarvisIpcBackend(state_dir, pairing_token)
    descriptor = backend.start()
    sys.stdout.write(json.dumps(descriptor.__dict__, separators=(",", ":")) + "\n")
    sys.stdout.flush()
    try:
        while not backend._stopped.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        backend.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
