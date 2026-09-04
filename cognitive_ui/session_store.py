"""Durable UI-session storage, intentionally separate from Stone 6 memory."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from .session_state import SessionState
from .dashboard_models import AgentStatus


class SessionStore:
    """Persist serialized :class:`SessionState` snapshots in a small SQLite DB."""

    def __init__(self, database_path: str | Path = "cognitive_ui_sessions.sqlite") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            str(self.database_path), check_same_thread=False, timeout=30.0
        )
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS ui_sessions (
                session_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        self._connection.commit()

    def save_session(
        self,
        session: SessionState | dict[str, Any],
        session_id: str | None = None,
    ) -> str:
        """Insert or replace a session snapshot and return its identifier."""

        # Accept the common ``save_session(session_id, snapshot)`` spelling too.
        if isinstance(session, str) and isinstance(session_id, (SessionState, dict)):
            session, session_id = session_id, session

        payload = self._snapshot(session)
        identifier = session_id or payload.get("active_session")
        if not identifier:
            raise ValueError("A session must contain an active_session identifier.")
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO ui_sessions(session_id, payload, updated_at) VALUES (?, ?, ?)",
                (identifier, json.dumps(payload, default=str, sort_keys=True), now),
            )
            self._connection.commit()
        return str(identifier)

    def load_session(self, session_id: str) -> SessionState | None:
        """Load one persisted session as a backward-compatible SessionState."""

        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM ui_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        return self._from_snapshot(json.loads(row[0]))

    def update_session(
        self,
        session_id: str,
        updates: SessionState | dict[str, Any],
    ) -> str:
        """Merge updates into a session, creating it if it does not yet exist."""

        current = self.load_session(session_id)
        base = current.snapshot() if current is not None else {"active_session": session_id}
        incoming = self._snapshot(updates)
        base.update(incoming)
        base["active_session"] = session_id
        return self.save_session(base, session_id=session_id)

    def clear_session(self, session_id: str | None = None) -> int:
        """Delete one session, or all UI sessions when no id is supplied."""

        with self._lock:
            if session_id is None:
                cursor = self._connection.execute("DELETE FROM ui_sessions")
            else:
                cursor = self._connection.execute(
                    "DELETE FROM ui_sessions WHERE session_id = ?", (session_id,)
                )
            self._connection.commit()
            return cursor.rowcount

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @staticmethod
    def _snapshot(session: SessionState | dict[str, Any]) -> dict[str, Any]:
        if isinstance(session, SessionState):
            return session.snapshot()
        if not isinstance(session, dict):
            raise TypeError("Session must be a SessionState or dictionary.")
        return dict(session)

    @staticmethod
    def _from_snapshot(snapshot: dict[str, Any]) -> SessionState:
        started_at = snapshot.get("started_at")
        state = SessionState(
            active_session=str(snapshot.get("active_session")),
            current_task=snapshot.get("current_task"),
            last_response=snapshot.get("last_response"),
        )
        if isinstance(started_at, str):
            try:
                state.started_at = datetime.fromisoformat(started_at)
            except ValueError:
                pass
        agents = snapshot.get("active_agents")
        if isinstance(agents, dict):
            for name, value in agents.items():
                if isinstance(value, dict):
                    state.active_agents[str(name)] = AgentStatus(
                        name=str(value.get("name", name)),
                        status=str(value.get("status", "idle")),
                        current_task=value.get("current_task"),
                    )
        workflow = snapshot.get("workflow_status")
        if isinstance(workflow, dict):
            state.update_workflow(workflow)
        return state

    def __enter__(self) -> "SessionStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
