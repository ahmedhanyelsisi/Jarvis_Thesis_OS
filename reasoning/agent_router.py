"""Registry-aware deterministic routing for Stone 5 tasks."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class AgentRouter:
    """Select an existing registered agent using ordered keyword rules."""

    _RULES: tuple[tuple[tuple[str, ...], str], ...] = (
        (("review", "evaluate", "critique", "consistency", "quality"), "reviewer_agent"),
        (("literature", "paper", "article", "research", "study"), "literature_agent"),
        (("latex", "tex", "equation", "typeset", "format"), "latex_agent"),
        (("diagram", "figure", "visual", "architecture"), "diagram_agent"),
        (("test", "verify", "validation"), "test_agent"),
        (("write", "draft", "chapter", "outline", "objective"), "thesis_writer_agent"),
    )

    def __init__(self, registry: Any | Iterable[str] | None = None) -> None:
        self.registry = registry

    def route(self, task: str, preferred_agent: str | None = None) -> str:
        """Return the best available agent name for *task*.

        ``writer_agent`` is treated as a capability alias for the existing
        ``thesis_writer_agent`` implementation; no replacement agent is created.
        """

        candidate = self._canonical_name(preferred_agent) if preferred_agent else None
        if candidate and self._is_available(candidate):
            return candidate

        normalized = task.lower()
        for keywords, agent_name in self._RULES:
            if any(keyword in normalized for keyword in keywords):
                if self._is_available(agent_name):
                    return agent_name

        fallback = "thesis_writer_agent"
        if self._is_available(fallback):
            return fallback

        available = self._available_names()
        if available:
            return available[0]
        raise LookupError("No registered agent is available for task routing.")

    def select_agent(self, task: str, preferred_agent: str | None = None) -> str:
        """Alias describing the routing operation in orchestration terms."""

        return self.route(task, preferred_agent)

    @staticmethod
    def _canonical_name(name: str | None) -> str | None:
        aliases = {"writer_agent": "thesis_writer_agent"}
        return aliases.get(name, name)

    def _available_names(self) -> list[str]:
        if self.registry is None:
            return [agent for _, agent in self._RULES]
        if hasattr(self.registry, "list_agents"):
            return list(self.registry.list_agents())
        return list(self.registry)

    def _is_available(self, agent_name: str) -> bool:
        return self.registry is None or agent_name in self._available_names()
