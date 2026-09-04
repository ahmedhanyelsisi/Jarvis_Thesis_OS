"""SQLite persistence for the Stone 6 memory subsystem."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Iterator, Sequence
from uuid import uuid4

from .memory_models import MemoryRecord, normalize_memory_type, utc_now


class MemoryStore:
    """Transaction-safe SQLite repository for memory records."""

    def __init__(self, database_path: str | Path = "memory_database.sqlite") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            str(self.database_path), check_same_thread=False, timeout=30.0
        )
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 30000")
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._initialize_schema()

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL CHECK (
                    memory_type IN (
                        'session_memory',
                        'project_memory',
                        'user_preference_memory',
                        'decision_memory',
                        'experience_memory'
                    )
                ),
                content TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                importance_score REAL NOT NULL DEFAULT 0.5
                    CHECK (importance_score >= 0.0 AND importance_score <= 1.0),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0 CHECK (access_count >= 0)
            );
            CREATE INDEX IF NOT EXISTS idx_memories_type
                ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_importance
                ON memories(importance_score DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_updated
                ON memories(updated_at DESC);
            """
        )
        self._connection.commit()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def create(
        self,
        memory_type: str,
        content: str,
        metadata: dict[str, Any],
        importance_score: float,
    ) -> MemoryRecord:
        memory_type = normalize_memory_type(memory_type)
        memory_id = str(uuid4())
        now = utc_now().isoformat()
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    memory_id, memory_type, content, metadata, importance_score,
                    created_at, updated_at, last_accessed, access_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    memory_id,
                    memory_type,
                    content,
                    json.dumps(metadata, default=str, sort_keys=True),
                    importance_score,
                    now,
                    now,
                    now,
                ),
            )
        record = self.get(memory_id, touch=False)
        assert record is not None
        return record

    def get(self, memory_id: str, *, touch: bool = True) -> MemoryRecord | None:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM memories WHERE memory_id = ?", (memory_id,)
            ).fetchone()
            if row is None:
                return None
            if touch:
                now = utc_now().isoformat()
                connection.execute(
                    """
                    UPDATE memories
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE memory_id = ?
                    """,
                    (now, memory_id),
                )
                row = dict(row)
                row["last_accessed"] = now
                row["access_count"] += 1
        return self._row_to_record(row)

    def update(self, memory_id: str, changes: dict[str, Any]) -> MemoryRecord | None:
        if not changes:
            return self.get(memory_id, touch=False)
        allowed = {"memory_type", "content", "metadata", "importance_score"}
        if not set(changes).issubset(allowed):
            raise ValueError("Unsupported memory update field.")
        values: list[Any] = []
        assignments: list[str] = []
        for field_name, value in changes.items():
            if field_name == "memory_type":
                value = normalize_memory_type(value)
            elif field_name == "metadata":
                value = json.dumps(value, default=str, sort_keys=True)
            assignments.append(f"{field_name} = ?")
            values.append(value)
        assignments.append("updated_at = ?")
        values.append(utc_now().isoformat())
        values.append(memory_id)
        with self._transaction() as connection:
            cursor = connection.execute(
                f"UPDATE memories SET {', '.join(assignments)} WHERE memory_id = ?",
                values,
            )
            if cursor.rowcount == 0:
                return None
        return self.get(memory_id, touch=False)

    def delete(self, memory_id: str) -> bool:
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE memory_id = ?", (memory_id,)
            )
        return cursor.rowcount > 0

    def list_candidates(
        self,
        *,
        memory_type: str | None = None,
        importance_threshold: float = 0.0,
    ) -> list[MemoryRecord]:
        parameters: list[Any] = [importance_threshold]
        sql = "SELECT * FROM memories WHERE importance_score >= ?"
        if memory_type is not None:
            sql += " AND memory_type = ?"
            parameters.append(normalize_memory_type(memory_type))
        with self._lock:
            rows = self._connection.execute(sql, parameters).fetchall()
        return [self._row_to_record(row) for row in rows]

    def touch_many(self, memory_ids: Sequence[str]) -> datetime:
        now = utc_now()
        unique_ids = list(dict.fromkeys(memory_ids))
        if not unique_ids:
            return now
        with self._transaction() as connection:
            connection.executemany(
                """
                UPDATE memories
                SET last_accessed = ?, access_count = access_count + 1
                WHERE memory_id = ?
                """,
                [(now.isoformat(), memory_id) for memory_id in unique_ids],
            )
        return now

    def clear_type(self, memory_type: str) -> int:
        memory_type = normalize_memory_type(memory_type)
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE memory_type = ?", (memory_type,)
            )
        return cursor.rowcount

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row | dict[str, Any]) -> MemoryRecord:
        data = dict(row)
        try:
            metadata = json.loads(data["metadata"])
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return MemoryRecord(
            memory_id=data["memory_id"],
            memory_type=data["memory_type"],
            content=data["content"],
            metadata=metadata,
            importance_score=float(data["importance_score"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=int(data["access_count"]),
        )

