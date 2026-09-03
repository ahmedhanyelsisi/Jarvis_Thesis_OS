"""Thread-safe persistent topic and paper memory."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..database.sqlite_utils import SQLiteDatabase


class ResearchMemory:
    """Remember research topics and papers using per-operation connections."""

    VALID_TYPES = frozenset({"topic", "paper"})

    def __init__(self, database_path: str | Path | None = None) -> None:
        default_path = (
            Path(__file__).resolve().parents[2]
            / "04_KNOWLEDGE_SYSTEM"
            / "data"
            / "research_memory.sqlite3"
        )
        self.database_path = Path(database_path or default_path).expanduser().resolve()
        self._database = SQLiteDatabase(self.database_path)
        self._create_schema()

    def _create_schema(self) -> None:
        with self._database.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_memory (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL CHECK(memory_type IN ('topic', 'paper')),
                    value TEXT NOT NULL,
                    context TEXT NOT NULL,
                    date_added TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_research_memory_type "
                "ON research_memory(memory_type)"
            )

    def remember_topic(
        self,
        topic: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("Topic cannot be empty.")
        return self._remember("topic", topic.strip(), context or {})

    def remember_paper(
        self,
        paper: str | dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> str:
        if isinstance(paper, dict):
            if not paper:
                raise ValueError("Paper cannot be empty.")
            value = json.dumps(paper, ensure_ascii=False, sort_keys=True)
            paper_context = dict(context or {})
            paper_context["structured"] = True
        elif isinstance(paper, str) and paper.strip():
            value = paper.strip()
            paper_context = context or {}
        else:
            raise ValueError("Paper must be a non-empty string or dictionary.")
        return self._remember("paper", value, paper_context)

    def _remember(
        self,
        memory_type: str,
        value: str,
        context: dict[str, Any],
    ) -> str:
        identifier = str(uuid.uuid4())
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO research_memory (
                    id, memory_type, value, context, date_added
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    identifier,
                    memory_type,
                    value,
                    json.dumps(context, ensure_ascii=False, sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return identifier

    def get_memory(
        self,
        memory_type: str | None = None,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if memory_type is not None and memory_type not in self.VALID_TYPES:
            raise ValueError(f"memory_type must be one of {sorted(self.VALID_TYPES)}.")
        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1.")
        query = "SELECT * FROM research_memory"
        parameters: list[Any] = []
        if memory_type is not None:
            query += " WHERE memory_type = ?"
            parameters.append(memory_type)
        query += " ORDER BY date_added DESC, id DESC"
        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)
        with self._database.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        memories: list[dict[str, Any]] = []
        for row in rows:
            memory = dict(row)
            memory["context"] = json.loads(memory["context"])
            if memory["memory_type"] == "paper" and memory["context"].get("structured"):
                memory["value"] = json.loads(memory["value"])
            memories.append(memory)
        return memories

    def clear_memory(self, memory_type: str | None = None) -> int:
        if memory_type is not None and memory_type not in self.VALID_TYPES:
            raise ValueError(f"memory_type must be one of {sorted(self.VALID_TYPES)}.")
        query = "DELETE FROM research_memory"
        parameters: tuple[str, ...] = ()
        if memory_type is not None:
            query += " WHERE memory_type = ?"
            parameters = (memory_type,)
        with self._database.connection() as connection:
            cursor = connection.execute(query, parameters)
        return cursor.rowcount

    def close(self) -> None:
        self._database.close()

    def __enter__(self) -> "ResearchMemory":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
