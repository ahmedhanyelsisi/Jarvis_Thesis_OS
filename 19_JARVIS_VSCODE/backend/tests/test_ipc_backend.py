from __future__ import annotations

import json
import sys
import threading
from multiprocessing.connection import Client
from pathlib import Path

import pytest

MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from backend.ipc.backend_server import AlreadyRunning, JarvisIpcBackend
from backend.ipc.protocol import MAX_MESSAGE_BYTES, PROTOCOL_VERSION


def connect(backend: JarvisIpcBackend):
    return Client(backend.descriptor.pipe_name, family="AF_PIPE", authkey=backend._pairing_token)


def request(connection, request_id, method, params=None):
    connection.send_bytes(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}).encode())
    return json.loads(connection.recv_bytes().decode())


@pytest.fixture
def backend(tmp_path: Path):
    server = JarvisIpcBackend(tmp_path / "state", b"a" * 32)
    server.start()
    yield server
    server.stop()


def initialize(connection):
    response = request(connection, "init", "initialize", {"client_id": "VS_CODE_CLIENT", "protocol_version": PROTOCOL_VERSION})
    assert response["result"]["backend"] == "ONLINE"


def test_safe_methods_return_sanitized_health(backend):
    with connect(backend) as connection:
        initialize(connection)
        assert request(connection, "ping", "ping")["result"]["pong"] is True
        assert request(connection, "version", "get_version")["result"]["protocol_version"] == PROTOCOL_VERSION
        health = request(connection, "health", "get_health")["result"]
        assert health == {"backend": "ONLINE", "jarvis_runtime": "NOT_ATTACHED", "protocol_version": PROTOCOL_VERSION}


@pytest.mark.parametrize("payload", [b"not-json", b'{"jsonrpc":"1.0","id":1,"method":"ping"}', b'{"jsonrpc":"2.0","method":"ping"}'])
def test_malformed_requests_fail_closed(backend, payload):
    with connect(backend) as connection:
        connection.send_bytes(payload)
        assert json.loads(connection.recv_bytes().decode())["error"]["code"] == -32600


def test_unknown_method_and_preinitialize_request_are_rejected(backend):
    with connect(backend) as connection:
        assert request(connection, "first", "ping")["error"]["code"] == -32001
        initialize(connection)
        assert request(connection, "unknown", "not_allowed")["error"]["code"] == -32600


def test_oversized_message_is_rejected(backend):
    with connect(backend) as connection:
        connection.send_bytes(b"x" * (MAX_MESSAGE_BYTES + 1))
        # The transport enforces MAX_MESSAGE_BYTES before JSON-RPC parsing.
        # On Windows AF_PIPE, multiprocessing closes this malicious connection
        # rather than sending a JSON-RPC response for a frame it refused to read.
        with pytest.raises((EOFError, BrokenPipeError, OSError)):
            connection.recv_bytes()
    # The rejected peer must not take down the singleton backend.
    with connect(backend) as fresh_connection:
        initialize(fresh_connection)
        assert request(fresh_connection, "after-oversize", "ping")["result"]["pong"] is True


def test_single_instance_rejects_second_live_backend(tmp_path: Path):
    first = JarvisIpcBackend(tmp_path / "state", b"a" * 32)
    first.start()
    try:
        with pytest.raises(AlreadyRunning):
            JarvisIpcBackend(tmp_path / "state", b"b" * 32).start()
        with connect(first) as connection:
            initialize(connection)
            assert request(connection, "first-still-healthy", "ping")["result"]["pong"] is True
    finally:
        first.stop()
    replacement = JarvisIpcBackend(tmp_path / "state", b"c" * 32)
    try:
        replacement.start()
        assert replacement.descriptor.owner_pid > 0
    finally:
        replacement.stop()


def test_second_compatible_client_attaches_to_the_same_backend(backend):
    with connect(backend) as first, connect(backend) as second:
        initialize(first)
        initialize(second)
        assert request(first, "one", "get_version")["result"]["backend_version"] == "0.1.0"
        assert request(second, "two", "ping")["result"]["pong"] is True


def test_stale_descriptor_is_replaced(tmp_path: Path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "backend.json").write_text('{"owner_pid":-1}', encoding="utf-8")
    server = JarvisIpcBackend(state_dir, b"a" * 32)
    try:
        server.start()
        assert server.descriptor.owner_pid > 0
    finally:
        server.stop()


def test_owner_shutdown_and_disconnect_are_safe(backend):
    with connect(backend) as connection:
        initialize(connection)
        assert request(connection, "no", "shutdown_if_owner", {"owner_instance_id": "wrong"})["error"]["code"] == -32003
    with connect(backend) as connection:
        initialize(connection)
        assert request(connection, "yes", "shutdown_if_owner", {"owner_instance_id": backend.descriptor.instance_id})["result"]["shutdown"] is True
    assert threading.Event().wait(0.1) is False
