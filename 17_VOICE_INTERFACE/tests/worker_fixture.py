"""Deterministic subprocess fixture; never selectable by production config."""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jarvis_voice.worker import WorkerServer


class FixtureRuntime:
    def status(self):
        return {"fixture": True}

    def devices(self):
        return []

    def listen(self, mode, cancel, event):
        event("listening")
        if cancel.wait(5):
            raise InterruptedError("Fixture capture cancelled")
        raise TimeoutError("Fixture wait expired")

    def speak(self, text, cancel, event):
        event("speaking")
        if text == "hang":
            threading.Event().wait(10)  # intentionally uncooperative inference
        return {"spoken": text}

    def stop(self):
        pass


WorkerServer(FixtureRuntime(), sys.stdin.buffer, sys.stdout.buffer).serve()
