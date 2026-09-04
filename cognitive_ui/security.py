"""Local deterministic command-safety validation for the UI boundary."""

from __future__ import annotations

import re
from dataclasses import dataclass


UNSAFE_PATTERNS = (
    r"\b(delete|remove|erase|destroy|drop|truncate|format)\b",
    r"(?:^|\s)(?:rm|rmdir|del|shutdown|reboot)(?:\s|$)",
    r"\b(?:os\.system|subprocess|powershell|cmd\.exe)\b",
)


@dataclass(frozen=True)
class CommandValidation:
    valid: bool
    requires_confirmation: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "requires_confirmation": self.requires_confirmation,
            "reason": self.reason,
        }


def is_unsafe_action(command: str) -> bool:
    """Return whether a command resembles a destructive/system action."""

    text = str(command).strip()
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in UNSAFE_PATTERNS)


def requires_confirmation(command: str) -> bool:
    return is_unsafe_action(command)


def validate_command(command: str, *, confirmed: bool = False) -> CommandValidation:
    """Validate a command before it reaches any kernel or agent boundary."""

    if not isinstance(command, str) or not command.strip():
        return CommandValidation(False, reason="Command must be a non-empty string.")
    if is_unsafe_action(command) and not confirmed:
        return CommandValidation(
            False,
            requires_confirmation=True,
            reason="Potentially destructive action requires explicit confirmation.",
        )
    return CommandValidation(True)


class SecurityValidator:
    """Object-oriented facade for applications that inject validators."""

    validate = staticmethod(validate_command)
