"""Transport-independent conversation and capability contracts."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChatReply:
    status: str
    text: str
    proposal_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PreparedAction:
    capability: str
    agent: str
    scope: str
    target: str
    source_version: str
    permission: str
    resource: str
    payload_json: str = "{}"
    mutating: bool = False
