"""Small, strict JSON-RPC 2.0 contract used by the Stone 28A pipe."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

PROTOCOL_VERSION = "28A.1"
MAX_MESSAGE_BYTES = 64 * 1024
ALLOWED_METHODS = frozenset({"initialize", "ping", "get_version", "get_health", "detach", "shutdown_if_owner"})


@dataclass(frozen=True)
class Request:
    request_id: str | int
    method: str
    params: dict[str, Any]


class ProtocolError(ValueError):
    """A request that cannot cross the transport boundary."""


def parse_request(payload: bytes) -> Request:
    if not payload or len(payload) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message size is invalid")
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid JSON") from exc
    if not isinstance(document, dict) or document.get("jsonrpc") != "2.0":
        raise ProtocolError("JSON-RPC version must be 2.0")
    request_id = document.get("id")
    if request_id is None or not isinstance(request_id, (str, int)) or isinstance(request_id, bool):
        raise ProtocolError("request id is required")
    method = document.get("method")
    if method not in ALLOWED_METHODS:
        raise ProtocolError("method is not allowed")
    params = document.get("params", {})
    if not isinstance(params, dict):
        raise ProtocolError("params must be an object")
    return Request(request_id=request_id, method=method, params=params)


def result(request_id: str | int, value: dict[str, Any]) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": value}, separators=(",", ":")).encode("utf-8")


def error(request_id: str | int | None, code: int, message: str) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}, separators=(",", ":")).encode("utf-8")
