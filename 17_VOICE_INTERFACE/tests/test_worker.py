import sys
import threading
import time
from pathlib import Path
import pytest
from jarvis_voice.client import WorkerClient, WorkerError


@pytest.fixture
def client(monkeypatch, tmp_path):
    import jarvis_voice.client as module
    real_popen = module.subprocess.Popen
    fixture = Path(__file__).with_name("worker_fixture.py")
    def popen(arguments, **kwargs):
        return real_popen([sys.executable, "-B", str(fixture)], **kwargs)
    monkeypatch.setattr(module.subprocess, "Popen", popen)
    config = tmp_path / "config.json"
    config.write_text("{}")
    worker = WorkerClient(sys.executable, config)
    yield worker
    worker.close()


def test_real_subprocess_roundtrips_do_not_race_busy_state(client):
    for _ in range(30):
        assert client.request("status", timeout=3) == {"fixture": True}


def test_real_subprocess_cooperative_cancel(client):
    started = threading.Event()
    results = []
    client.event_callback = lambda identifier, payload: started.set()
    def listen():
        try:
            client.request("listen", {"mode": "ptt"}, timeout=3)
        except InterruptedError:
            results.append("cancelled")
    thread = threading.Thread(target=listen)
    thread.start()
    assert started.wait(3)
    assert client.stop()
    thread.join(3)
    assert not thread.is_alive()
    assert results == ["cancelled"]
    assert client.alive


def test_uncooperative_worker_is_terminated(client):
    started = threading.Event()
    client.event_callback = lambda identifier, payload: started.set()
    result = []
    def speak():
        try:
            client.request("speak", {"text": "hang"}, timeout=3)
        except (WorkerError, InterruptedError):
            result.append("stopped")
    thread = threading.Thread(target=speak)
    thread.start()
    assert started.wait(3)
    before = time.monotonic()
    assert not client.stop(timeout=.2)
    thread.join(2)
    assert time.monotonic() - before < 2
    assert result == ["stopped"]
    assert not client.alive


def test_timeout_terminates_worker(client):
    with pytest.raises(WorkerError, match="timed out"):
        client.request("speak", {"text": "hang"}, timeout=.2)
    assert not client.alive


def test_unknown_operation_closes_protocol(client):
    with pytest.raises(WorkerError):
        client.request("execute_os_command", timeout=2)


def test_close_is_idempotent(client):
    client.close()
    client.close()
    assert not client.alive
