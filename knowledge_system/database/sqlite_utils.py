"""Thread-safe, short-lived SQLite connection management."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator


class SQLiteDatabase:
    """Open a fresh SQLite connection for every serialized operation."""

    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._closed = False
        self._initialize_journal()

    def _initialize_journal(self) -> None:
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a per-operation connection and always commit/rollback/close it."""

        with self._lock:
            if self._closed:
                raise RuntimeError("Database has been closed.")
            connection = sqlite3.connect(
                str(self.path),
                timeout=30.0,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def close(self) -> None:
        """Prevent new operations; active operations close their own connections."""

        with self._lock:
            self._closed = True
