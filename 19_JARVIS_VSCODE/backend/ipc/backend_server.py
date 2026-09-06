"""Windows named-pipe foundation; it deliberately exposes no JARVIS authority."""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from multiprocessing.connection import Client, Connection, Listener
from pathlib import Path
from typing import Any

from .protocol import MAX_MESSAGE_BYTES, PROTOCOL_VERSION, ProtocolError, error, parse_request, result

BACKEND_VERSION = "0.1.0"


class AlreadyRunning(RuntimeError):
    """A live backend descriptor already owns the local singleton."""


@dataclass(frozen=True)
class BackendDescriptor:
    protocol_version: str
    backend_version: str
    instance_id: str
    pipe_name: str
    owner_pid: int
    started_at: str


class JarvisIpcBackend:
    """A deliberately small, authenticated pipe server for the VS Code client."""

    def __init__(self, state_dir: Path, pairing_token: bytes | None = None) -> None:
        self._state_dir = state_dir
        self._pairing_token = pairing_token or secrets.token_bytes(32)
        self._instance_id = str(uuid.uuid4())
        self._pipe_name = rf"\\.\pipe\jarvis-thesis-28a-{self._instance_id}"
        self._listener: Listener | None = None
        self._accept_thread: threading.Thread | None = None
        self._stopped = threading.Event()
        self._workers: set[threading.Thread] = set()
        self._workers_lock = threading.Lock()
        self._stop_lock = threading.Lock()
        self._lock_path = state_dir / "backend.lock"
        self._descriptor_path = state_dir / "backend.json"
        self._descriptor: BackendDescriptor | None = None

    @property
    def descriptor(self) -> BackendDescriptor:
        if self._descriptor is None:
            raise RuntimeError("backend has not started")
        return self._descriptor

    def start(self) -> BackendDescriptor:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._acquire_singleton()
        try:
            self._listener = Listener(self._pipe_name, family="AF_PIPE", authkey=self._pairing_token)
            self._descriptor = BackendDescriptor(
                protocol_version=PROTOCOL_VERSION,
                backend_version=BACKEND_VERSION,
                instance_id=self._instance_id,
                pipe_name=self._pipe_name,
                owner_pid=os.getpid(),
                started_at=datetime.now(UTC).isoformat(),
            )
            self._descriptor_path.write_text(json.dumps(asdict(self._descriptor), separators=(",", ":")), encoding="utf-8")
            self._accept_thread = threading.Thread(target=self._accept_loop, name="jarvis-ipc-accept", daemon=True)
            self._accept_thread.start()
            return self._descriptor
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        with self._stop_lock:
            if self._stopped.is_set():
                return
            self._stopped.set()
            listener = self._listener
            if listener is not None:
                # AF_PIPE close alone does not reliably wake a blocking accept
                # on Windows. Wake it through the existing authenticated pipe
                # before closing the listener, avoiding a close/wake race.
                self._wake_accept_loop()
                listener.close()
            self._listener = None
        self._join_threads()
        for path in (self._descriptor_path, self._lock_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _wake_accept_loop(self) -> None:
        try:
            connection = Client(self._pipe_name, family="AF_PIPE", authkey=self._pairing_token)
            connection.close()
        except (EOFError, OSError):
            # The listener can have already closed; either outcome is safe.
            pass

    def _join_threads(self) -> None:
        current = threading.current_thread()
        if self._accept_thread is not None and self._accept_thread is not current:
            self._accept_thread.join(timeout=1.0)
        with self._workers_lock:
            workers = tuple(self._workers)
        for worker in workers:
            if worker is not current:
                worker.join(timeout=1.0)

    def _acquire_singleton(self) -> None:
        try:
            descriptor = json.loads(self._descriptor_path.read_text(encoding="utf-8"))
            if self._process_alive(int(descriptor.get("owner_pid", -1))):
                raise AlreadyRunning("a compatible backend descriptor is already live")
        except FileNotFoundError:
            pass
        except (ValueError, json.JSONDecodeError):
            pass
        for stale_path in (self._descriptor_path, self._lock_path):
            try:
                stale_path.unlink()
            except FileNotFoundError:
                pass
        try:
            descriptor_handle = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise AlreadyRunning("backend lock is held") from exc
        with os.fdopen(descriptor_handle, "w", encoding="utf-8") as lock_file:
            lock_file.write(self._instance_id)

    @staticmethod
    def _process_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _accept_loop(self) -> None:
        while not self._stopped.is_set() and self._listener is not None:
            try:
                connection = self._listener.accept()
            except (OSError, EOFError):
                break
            worker = threading.Thread(target=self._serve_connection, args=(connection,), daemon=True)
            with self._workers_lock:
                self._workers.add(worker)
            worker.start()

    def _serve_connection(self, connection: Connection) -> None:
        initialized = False
        try:
            while not self._stopped.is_set():
                try:
                    payload = connection.recv_bytes(MAX_MESSAGE_BYTES)
                except (EOFError, OSError):
                    return
                try:
                    request = parse_request(payload)
                    if not initialized and request.method != "initialize":
                        connection.send_bytes(error(request.request_id, -32001, "initialize is required"))
                        continue
                    response, initialized = self._dispatch(request.method, request.params, request.request_id, initialized)
                    connection.send_bytes(response)
                except ProtocolError as exc:
                    connection.send_bytes(error(None, -32600, str(exc)))
                except Exception:
                    connection.send_bytes(error(None, -32603, "internal IPC error"))
        finally:
            connection.close()
            with self._workers_lock:
                self._workers.discard(threading.current_thread())

    def _dispatch(self, method: str, params: dict[str, Any], request_id: str | int, initialized: bool) -> tuple[bytes, bool]:
        if method == "initialize":
            if params.get("client_id") != "VS_CODE_CLIENT" or params.get("protocol_version") != PROTOCOL_VERSION:
                return error(request_id, -32002, "unsupported client identity or protocol"), False
            return result(request_id, {"backend": "ONLINE", "instance_id": self._instance_id, "protocol_version": PROTOCOL_VERSION}), True
        if method == "ping":
            return result(request_id, {"pong": True, "timestamp": time.time()}), initialized
        if method == "get_version":
            return result(request_id, {"protocol_version": PROTOCOL_VERSION, "backend_version": BACKEND_VERSION}), initialized
        if method == "get_health":
            return result(request_id, {"backend": "ONLINE", "jarvis_runtime": "NOT_ATTACHED", "protocol_version": PROTOCOL_VERSION}), initialized
        if method == "detach":
            return result(request_id, {"detached": True}), initialized
        if method == "shutdown_if_owner":
            if params.get("owner_instance_id") != self._instance_id:
                return error(request_id, -32003, "backend ownership mismatch"), initialized
            response = result(request_id, {"shutdown": True})
            threading.Thread(target=self.stop, daemon=True).start()
            return response, initialized
        return error(request_id, -32601, "method is not allowed"), initialized
