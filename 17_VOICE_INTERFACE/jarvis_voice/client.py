"""Bounded subprocess client with concurrent cancellation and late-message rejection."""
import os
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path
from .protocol import VERSION, encode, read_message


class WorkerError(RuntimeError):
    pass


class WorkerClient:
    def __init__(self, python, config, *, event_callback=None):
        package_root = Path(__file__).resolve().parents[1]
        repository = package_root.parent
        self.python = str(Path(python).resolve(strict=True))
        self.config = str(Path(config).resolve(strict=True))
        self.event_callback = event_callback or (lambda identifier, payload: None)
        self.__pending = {}
        self.__lock = threading.RLock()
        self.__write = threading.Lock()
        self.__closed = threading.Event()
        self.__active = None
        environment = os.environ.copy()
        environment.update(PYTHONPATH=os.pathsep.join((str(package_root), str(repository))),
                           HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                           PYTHONDONTWRITEBYTECODE="1")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.__process = subprocess.Popen([self.python, "-B", "-m", "jarvis_voice.worker", "--config", self.config],
             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
             env=environment, cwd=repository, creationflags=flags, shell=False)
        self.__reader = threading.Thread(target=self._read, daemon=True, name="jarvis-voice-ipc")
        self.__reader.start()

    @property
    def alive(self):
        return not self.__closed.is_set() and self.__process.poll() is None

    def _fail_pending(self, reason):
        with self.__lock:
            for mailbox in self.__pending.values():
                try:
                    mailbox.put_nowait({"kind": "error", "payload": {"code": "worker_lost", "message": reason}})
                except queue.Full:
                    pass

    def _read(self):
        try:
            while not self.__closed.is_set():
                message = read_message(self.__process.stdout)
                if set(message) != {"version", "id", "kind", "payload"} or message["kind"] not in ("event", "result", "error"):
                    raise ValueError("Invalid worker response")
                with self.__lock:
                    mailbox = self.__pending.get(message["id"])
                if mailbox is None:
                    continue
                if message["kind"] == "event":
                    payload = message["payload"]
                    if not isinstance(payload, dict) or set(payload) != {"state"} or payload["state"] not in ("ready", "listening", "transcribing", "speaking"):
                        raise ValueError("Invalid worker state")
                    self.event_callback(message["id"], payload)
                else:
                    mailbox.put_nowait(message)
        except Exception as exc:
            self.__closed.set()
            self._fail_pending(f"Voice worker unavailable: {type(exc).__name__}")
            self.terminate()

    def request(self, operation, payload=None, *, timeout=30, on_started=None):
        identifier = uuid.uuid4().hex
        mailbox = queue.Queue(maxsize=1)
        with self.__lock:
            if not self.alive:
                raise WorkerError("Voice worker is not running")
            if operation in ("listen", "speak"):
                if self.__active is not None:
                    raise WorkerError("A voice operation is already active")
                self.__active = identifier
            self.__pending[identifier] = mailbox
        try:
            if on_started:
                on_started(identifier)
            message = {"version": VERSION, "id": identifier, "operation": operation, "payload": payload or {}}
            with self.__write:
                self.__process.stdin.write(encode(message))
                self.__process.stdin.flush()
            try:
                response = mailbox.get(timeout=timeout)
            except queue.Empty:
                self.terminate()
                raise WorkerError("Voice operation timed out; worker terminated")
            if response["kind"] == "error":
                details = response["payload"]
                if not isinstance(details, dict):
                    raise WorkerError("Invalid worker error")
                if details.get("code") == "cancelled":
                    raise InterruptedError(details.get("message", "Cancelled"))
                raise WorkerError(str(details.get("message", "Voice operation failed")))
            return response["payload"]
        except InterruptedError:
            raise
        except (BrokenPipeError, OSError):
            self.terminate()
            raise WorkerError("Voice worker disconnected")
        finally:
            with self.__lock:
                self.__pending.pop(identifier, None)
                if self.__active == identifier:
                    self.__active = None

    def stop(self, timeout=.75):
        with self.__lock:
            active = self.__active
        if active is None:
            return True
        deadline = time.monotonic() + timeout
        try:
            self.request("cancel", {"request_id": active}, timeout=min(.25, timeout))
        except (WorkerError, InterruptedError):
            self.terminate()
            return False
        while time.monotonic() < deadline:
            with self.__lock:
                if self.__active != active:
                    return True
            self.__closed.wait(.01)
        self.terminate()
        return False

    def terminate(self):
        self.__closed.set()
        self._fail_pending("Voice worker terminated")
        if self.__process.poll() is None:
            self.__process.terminate()
            try:
                self.__process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.__process.kill()
                self.__process.wait(timeout=1)

    def close(self):
        if self.alive:
            try:
                self.request("shutdown", timeout=1)
            except (WorkerError, InterruptedError):
                pass
        self.terminate()
        if self.__reader is not threading.current_thread():
            self.__reader.join(timeout=1)
        for stream in (self.__process.stdin, self.__process.stdout):
            if stream:
                stream.close()
