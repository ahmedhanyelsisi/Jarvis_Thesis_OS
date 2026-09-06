"""Volatile scope state; only its owning authorization manager may grant scopes."""
import math
import time


class ScopedAutonomousManager:
    SUPPORTED_SCOPES = ("thesis_writing", "research", "review", "compilation", "documentation")
    BLOCKED_ACTIONS = frozenset(("os_command", "file_deletion", "system_modification", "external_change", "delete", "rm", "sudo"))

    def __init__(self, *, owner_key=None, clock=time.monotonic):
        self.__key = owner_key if owner_key is not None else object()
        self.__clock = clock
        self._active_scopes = ()
        self._ttl_expiry = None

    def enable_scopes(self, scopes, ttl_seconds=900, *, owner_key=None):
        if owner_key is not self.__key:
            return False
        if (not isinstance(scopes, (list, tuple)) or not scopes
                or any(scope not in self.SUPPORTED_SCOPES for scope in scopes)
                or isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float))
                or not math.isfinite(ttl_seconds) or not 0 < ttl_seconds <= 900):
            return False
        self._active_scopes = tuple(sorted(set(scopes)))
        self._ttl_expiry = self.__clock() + ttl_seconds
        return True

    def get_active_scopes(self):
        if self._ttl_expiry is None or self.__clock() >= self._ttl_expiry:
            self.reset()
        return list(self._active_scopes)

    def is_scope_active(self, scope):
        return scope in self.get_active_scopes()

    def is_action_blocked(self, action):
        return action.lower() in self.BLOCKED_ACTIONS

    def reset(self):
        self._active_scopes = ()
        self._ttl_expiry = None
