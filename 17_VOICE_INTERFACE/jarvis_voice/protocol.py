"""Versioned JSON-lines IPC. No pickle, arbitrary function names, or network socket."""
import json
import re

VERSION = 1
MAX_MESSAGE_BYTES = 65536
OPERATIONS = frozenset(("status", "devices", "listen", "speak", "cancel", "shutdown"))


def encode(value):
    data = (json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValueError("IPC message too large")
    return data


def read_message(stream):
    raw = stream.readline(MAX_MESSAGE_BYTES + 1)
    if not raw:
        raise EOFError()
    if len(raw) > MAX_MESSAGE_BYTES or not raw.endswith(b"\n"):
        raise ValueError("Oversized or incomplete IPC message")
    message = json.loads(raw.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
    if not isinstance(message, dict) or type(message.get("version")) is not int or message["version"] != VERSION:
        raise ValueError("Unsupported IPC version")
    if not isinstance(message.get("id"), str) or not re.fullmatch(r"[a-f0-9]{32}", message["id"]):
        raise ValueError("Invalid request ID")
    return message


def validate_request(message):
    if set(message) != {"version", "id", "operation", "payload"}:
        raise ValueError("Unknown request fields")
    operation, payload = message["operation"], message["payload"]
    if operation not in OPERATIONS or not isinstance(payload, dict):
        raise ValueError("Unknown operation")
    expected = {"listen": {"mode"}, "speak": {"text"}, "cancel": {"request_id"}}.get(operation, set())
    if set(payload) != expected:
        raise ValueError("Invalid operation payload")
    if operation == "listen" and payload["mode"] not in ("ptt", "wake"):
        raise ValueError("Invalid capture mode")
    if operation == "speak" and (not isinstance(payload["text"], str) or not 0 < len(payload["text"]) <= 1000):
        raise ValueError("Speech text exceeds limit")
    if operation == "cancel" and (not isinstance(payload["request_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", payload["request_id"])):
        raise ValueError("Invalid cancellation target")
    return operation, payload
