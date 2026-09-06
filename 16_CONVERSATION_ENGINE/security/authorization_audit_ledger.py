"""Tamper-evident authorization audit storage.

The persistent backend uses Windows DPAPI for a per-user signing key and for the
latest sequence/head anchor. This detects edited, replaced, or rolled-back
ledger files while those DPAPI-protected artifacts remain available. DPAPI is
not a security boundary against arbitrary malicious code running as the same
interactive Windows user: that code can invoke DPAPI as that user. A future
``HighAssuranceWindowsServiceAuditBackend`` can move the key and anchor to a
separately protected service account.
"""
from __future__ import annotations

import copy
import ctypes
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path


_ZERO_HEAD = "0" * 64
_MAX_AUDIT_BYTES = 32 * 1024 * 1024
_MAX_EVENTS = 50_000
_DPAPI_ENTROPY = b"Jarvis.AuthorizationAudit.v1"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class AuditBackend(ABC):
    """Storage and key boundary used by :class:`AuthorizationAuditLedger`."""

    persistent = False

    @abstractmethod
    def load(self):
        """Return ``(entries, sequence, head)`` or raise on an unsafe state."""

    @abstractmethod
    def sign(self, canonical_event):
        """Authenticate a canonical event body and return a hex HMAC."""

    @abstractmethod
    def append(self, event):
        """Durably append an event before its anchor is advanced."""

    @abstractmethod
    def verify_anchor(self, sequence, head):
        """Confirm the protected anchor still matches the loaded ledger."""

    @abstractmethod
    def commit_anchor(self, sequence, head):
        """Durably advance the protected sequence/head anchor."""

    def read_entries(self):
        raise NotImplementedError


class MemoryAuditBackend(AuditBackend):
    """Non-persistent backend for an in-memory ledger."""

    def __init__(self):
        self._key = secrets.token_bytes(32)
        self._entries = []
        self._sequence = 0
        self._head = _ZERO_HEAD

    def load(self):
        return copy.deepcopy(self._entries), self._sequence, self._head

    def sign(self, canonical_event):
        return hmac.new(self._key, canonical_event, hashlib.sha256).hexdigest()

    def append(self, event):
        self._entries.append(copy.deepcopy(event))

    def verify_anchor(self, sequence, head):
        return (sequence, head) == (self._sequence, self._head)

    def commit_anchor(self, sequence, head):
        self._sequence, self._head = sequence, head


class WindowsDPAPIAuditBackend(AuditBackend):
    """Local backend with a DPAPI-protected signing key and sequence/head anchor."""

    persistent = True

    def __init__(self, path):
        if os.name != "nt":
            raise OSError("Windows DPAPI audit storage is only available on Windows")
        self.path = Path(path)
        self.key_path = self.path.with_name(self.path.name + ".key.dpapi")
        self.anchor_path = self.path.with_name(self.path.name + ".anchor.dpapi")
        self._key = None

    @staticmethod
    def _crypt(protect, data):
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        raw = ctypes.create_string_buffer(data, len(data))
        input_blob = DATA_BLOB(len(data), ctypes.cast(raw, ctypes.POINTER(ctypes.c_byte)))
        entropy_raw = ctypes.create_string_buffer(_DPAPI_ENTROPY, len(_DPAPI_ENTROPY))
        entropy = DATA_BLOB(len(_DPAPI_ENTROPY), ctypes.cast(entropy_raw, ctypes.POINTER(ctypes.c_byte)))
        output = DATA_BLOB()
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if protect:
            ok = crypt32.CryptProtectData(ctypes.byref(input_blob), "Jarvis authorization audit", ctypes.byref(entropy), None, None, 0, ctypes.byref(output))
        else:
            ok = crypt32.CryptUnprotectData(ctypes.byref(input_blob), None, ctypes.byref(entropy), None, None, 0, ctypes.byref(output))
        if not ok:
            raise OSError(ctypes.get_last_error(), "Windows DPAPI operation failed")
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            kernel32.LocalFree(output.pbData)

    @classmethod
    def _protect(cls, data):
        return cls._crypt(True, data)

    @classmethod
    def _unprotect(cls, data):
        return cls._crypt(False, data)

    @staticmethod
    def _atomic_write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp-" + secrets.token_hex(8))
        try:
            with temporary.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _write_protected_json(self, path, value):
        self._atomic_write(path, self._protect(_canonical(value)))

    def _read_protected_json(self, path):
        return json.loads(self._unprotect(path.read_bytes()).decode("utf-8"))

    def _read_events(self):
        if not self.path.exists():
            return []
        if self.path.stat().st_size > _MAX_AUDIT_BYTES:
            raise ValueError("Audit exceeds size limit")
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]

    def load(self):
        ledger_exists = self.path.exists()
        key_exists = self.key_path.exists()
        anchor_exists = self.anchor_path.exists()
        if not ledger_exists and not key_exists and not anchor_exists:
            self._key = secrets.token_bytes(32)
            self._atomic_write(self.key_path, self._protect(self._key))
            self._write_protected_json(self.anchor_path, {"version": 1, "sequence": 0, "head": _ZERO_HEAD})
            return [], 0, _ZERO_HEAD
        if not key_exists or not anchor_exists:
            raise ValueError("Audit key or protected anchor is missing")
        self._key = self._unprotect(self.key_path.read_bytes())
        if len(self._key) != 32:
            raise ValueError("Invalid audit signing key")
        anchor = self._read_protected_json(self.anchor_path)
        if set(anchor) != {"version", "sequence", "head"} or anchor["version"] != 1:
            raise ValueError("Invalid protected audit anchor")
        if not isinstance(anchor["sequence"], int) or anchor["sequence"] < 0:
            raise ValueError("Invalid protected audit sequence")
        if not isinstance(anchor["head"], str) or len(anchor["head"]) != 64:
            raise ValueError("Invalid protected audit head")
        entries = self._read_events()
        if not ledger_exists and anchor["sequence"]:
            raise ValueError("Audit ledger is missing")
        return entries, anchor["sequence"], anchor["head"]

    def sign(self, canonical_event):
        if self._key is None:
            raise RuntimeError("Audit backend has not been initialized")
        return hmac.new(self._key, canonical_event, hashlib.sha256).hexdigest()

    def append(self, event):
        with self.path.open("ab") as stream:
            stream.write(_canonical(event) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())

    def read_entries(self):
        return self._read_events()

    def verify_anchor(self, sequence, head):
        try:
            return self._read_protected_json(self.anchor_path) == {"version": 1, "sequence": sequence, "head": head}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def commit_anchor(self, sequence, head):
        self._write_protected_json(self.anchor_path, {"version": 1, "sequence": sequence, "head": head})


class HighAssuranceWindowsServiceAuditBackend(AuditBackend):
    """Extension point for a future service-account/key-isolated backend."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("A high-assurance Windows service audit backend is not installed")

    def load(self):  # pragma: no cover - documents the interface for implementers
        raise NotImplementedError

    def sign(self, canonical_event):
        raise NotImplementedError

    def append(self, event):
        raise NotImplementedError

    def verify_anchor(self, sequence, head):
        raise NotImplementedError

    def commit_anchor(self, sequence, head):
        raise NotImplementedError


class AuthorizationAuditLedger:
    """Owner-controlled, HMAC-authenticated audit chain that fails closed."""

    def __init__(self, *, owner_key=None, path=None, backend=None):
        if backend is not None and path is not None:
            raise ValueError("Specify an audit backend or a ledger path, not both")
        self.__owner_key = owner_key if owner_key is not None else object()
        self.path = Path(path) if path is not None else getattr(backend, "path", None)
        self.__backend = backend if backend is not None else (WindowsDPAPIAuditBackend(path) if path is not None else MemoryAuditBackend())
        self.__entries, self.__head, self.__healthy = [], _ZERO_HEAD, True
        self.__lock = threading.RLock()
        try:
            entries, sequence, head = self.__backend.load()
            if len(entries) > _MAX_EVENTS or not self._valid_chain(entries):
                raise ValueError("Invalid authenticated audit chain")
            actual_head = entries[-1]["event_hash"] if entries else _ZERO_HEAD
            if (sequence, head) != (len(entries), actual_head):
                raise ValueError("Protected audit anchor does not match ledger")
            self.__entries, self.__head = entries, actual_head
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            self.__healthy = False

    @staticmethod
    def _hash(event):
        return hashlib.sha256(_canonical(event)).hexdigest()

    def _valid_chain(self, entries):
        previous = _ZERO_HEAD
        for index, entry in enumerate(entries, 1):
            body = dict(entry)
            digest = body.pop("event_hash")
            authentication = body.pop("event_auth")
            if (body.get("sequence") != index or body.get("previous_hash") != previous
                    or self._hash(body) != digest or not isinstance(authentication, str)
                    or not hmac.compare_digest(self.__backend.sign(_canonical(body)), authentication)):
                return False
            previous = digest
        return True

    @property
    def entries(self):
        with self.__lock:
            return copy.deepcopy(self.__entries)

    def verify_integrity(self):
        with self.__lock:
            try:
                if not self.__healthy or not self._valid_chain(self.__entries):
                    return False
                expected = self.__entries[-1]["event_hash"] if self.__entries else _ZERO_HEAD
                if expected != self.__head or not self.__backend.verify_anchor(len(self.__entries), expected):
                    return False
                return not self.__backend.persistent or self.__backend.read_entries() == self.__entries
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                return False

    def record_event(self, *, owner_key=None, **fields):
        with self.__lock:
            if owner_key is not self.__owner_key:
                raise PermissionError("Only the authorization service owns the audit writer")
            if not self.verify_integrity():
                self.__healthy = False
                raise RuntimeError("Audit unavailable or altered; dispatch disabled")
            if len(self.__entries) >= _MAX_EVENTS:
                raise RuntimeError("Audit limit reached; archive before starting a new session")
            body = {"timestamp": time.time(), "fields": fields,
                    "sequence": len(self.__entries) + 1, "previous_hash": self.__head}
            event = dict(body)
            event["event_hash"] = self._hash(body)
            event["event_auth"] = self.__backend.sign(_canonical(body))
            try:
                # Append first: a crash before anchor update is fail-closed at restart.
                self.__backend.append(event)
                self.__backend.commit_anchor(event["sequence"], event["event_hash"])
            except (OSError, ValueError, TypeError):
                self.__healthy = False
                raise
            self.__entries.append(event)
            self.__head = event["event_hash"]
            return True
