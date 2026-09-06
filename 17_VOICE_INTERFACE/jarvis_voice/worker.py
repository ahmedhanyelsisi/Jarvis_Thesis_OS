"""Audio subprocess: fixed operations over inherited pipes, one active task."""
import argparse
import os
import sys
import threading
from .config import VoiceConfig
from .protocol import VERSION, encode, read_message, validate_request
from .providers import LocalVoiceRuntime


class WorkerServer:
    def __init__(self, runtime, incoming, outgoing):
        self.runtime = runtime
        self.incoming = incoming
        self.outgoing = outgoing
        self._write_lock = threading.Lock()
        self._lock = threading.RLock()
        self._active = None

    def send(self, identifier, kind, payload):
        with self._write_lock:
            self.outgoing.write(encode({"version": VERSION, "id": identifier, "kind": kind, "payload": payload}))
            self.outgoing.flush()

    def _run(self, identifier, operation, payload, cancel):
        def event(state):
            if not cancel.is_set():
                self.send(identifier, "event", {"state": state})
        try:
            if operation == "listen":
                value = self.runtime.listen(payload["mode"], cancel, event)
            elif operation == "speak":
                value = self.runtime.speak(payload["text"], cancel, event)
            elif operation == "status":
                value = self.runtime.status()
            elif operation == "devices":
                value = self.runtime.devices()
            else:
                raise ValueError("Unsupported operation")
            if cancel.is_set():
                raise InterruptedError("Operation cancelled")
            with self._lock:
                if self._active and self._active[0] == identifier:
                    self._active = None
            self.send(identifier, "result", value)
        except Exception as exc:
            with self._lock:
                if self._active and self._active[0] == identifier:
                    self._active = None
            self.send(identifier, "error", {"code": "cancelled" if isinstance(exc, InterruptedError) else type(exc).__name__,
                                           "message": str(exc)[:1000]})
        finally:
            with self._lock:
                if self._active and self._active[0] == identifier:
                    self._active = None

    def _cancel(self, identifier=None):
        with self._lock:
            active = self._active
            if active and (identifier is None or active[0] == identifier):
                active[1].set()
                self.runtime.stop()
                return active
        return None

    def serve(self):
        try:
            while True:
                message = read_message(self.incoming)
                operation, payload = validate_request(message)
                identifier = message["id"]
                if operation == "shutdown":
                    active = self._cancel()
                    if active:
                        active[2].join(timeout=.5)
                    self.send(identifier, "result", {"shutdown": True})
                    return
                if operation == "cancel":
                    active = self._cancel(payload["request_id"])
                    self.send(identifier, "result", {"cancellation_requested": active is not None})
                    continue
                with self._lock:
                    if self._active:
                        self.send(identifier, "error", {"code": "busy", "message": "Audio worker is busy"})
                        continue
                    cancel = threading.Event()
                    thread = threading.Thread(target=self._run, args=(identifier, operation, payload, cancel), daemon=True)
                    self._active = (identifier, cancel, thread)
                    thread.start()
        except EOFError:
            self._cancel()
        finally:
            active = self._cancel()
            if active:
                active[2].join(timeout=.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    # Libraries occasionally print to stdout. Reserve the original pipe for IPC.
    output = sys.stdout.buffer
    sys.stdout = sys.stderr
    try:
        WorkerServer(LocalVoiceRuntime(VoiceConfig.load(args.config)), sys.stdin.buffer, output).serve()
        return 0
    except Exception as exc:
        print(f"Voice worker stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
