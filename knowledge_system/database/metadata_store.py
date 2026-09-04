"""Thread-safe SQLite metadata catalog for research documents."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .sqlite_utils import SQLiteDatabase


_CORE_FIELDS = {
    "id",
    "filename",
    "document_type",
    "author",
    "date_added",
    "tags",
    "source",
    "document_hash",
    "status",
    "chunk_count",
    "owner_token",
}

PENDING = "PENDING"
PROCESSING = "PROCESSING"
READY = "READY"
FAILED = "FAILED"
INGESTION_STATES = frozenset({PENDING, PROCESSING, READY, FAILED})


class MetadataStore:
    """Persist normalized metadata with connection-per-operation safety."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        default_path = (
            Path(__file__).resolve().parents[2]
            / "04_KNOWLEDGE_SYSTEM"
            / "data"
            / "metadata.sqlite3"
        )
        self.database_path = Path(database_path or default_path).expanduser().resolve()
        self._database = SQLiteDatabase(self.database_path)
        self._create_and_migrate_schema()

    def _create_and_migrate_schema(self) -> None:
        with self._database.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    author TEXT,
                    date_added TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    source TEXT,
                    document_hash TEXT,
                    status TEXT NOT NULL DEFAULT 'READY',
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    owner_token TEXT,
                    extra_metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(documents)").fetchall()
            }
            migrations = {
                "document_hash": "ALTER TABLE documents ADD COLUMN document_hash TEXT",
                "status": (
                    "ALTER TABLE documents ADD COLUMN status TEXT NOT NULL DEFAULT 'READY'"
                ),
                "chunk_count": (
                    "ALTER TABLE documents ADD COLUMN chunk_count INTEGER NOT NULL DEFAULT 0"
                ),
                "owner_token": "ALTER TABLE documents ADD COLUMN owner_token TEXT",
                "extra_metadata": (
                    "ALTER TABLE documents ADD COLUMN extra_metadata TEXT NOT NULL DEFAULT '{}'"
                ),
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)
            connection.execute(
                "UPDATE documents SET status = UPPER(status) "
                "WHERE status != UPPER(status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_filename "
                "ON documents(filename)"
            )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_hash "
                "ON documents(document_hash) WHERE document_hash IS NOT NULL"
            )

    def add_document(
        self,
        metadata: dict[str, Any],
        *,
        document_id: str | None = None,
    ) -> str:
        """Add a metadata record and return its document ID."""

        filename = str(metadata.get("filename", "")).strip()
        document_type = str(metadata.get("document_type", "")).strip().lower()
        if not filename or not document_type:
            raise ValueError("Metadata requires filename and document_type.")

        identifier = document_id or str(uuid.uuid4())
        date_added = metadata.get("date_added") or datetime.now(timezone.utc).isoformat()
        tags = metadata.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        extra_metadata = {
            key: value for key, value in metadata.items() if key not in _CORE_FIELDS
        }

        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    id, filename, document_type, author, date_added, tags, source,
                    document_hash, status, chunk_count, owner_token, extra_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identifier,
                    filename,
                    document_type,
                    _optional_string(metadata.get("author")),
                    str(date_added),
                    json.dumps(normalized_tags, ensure_ascii=False),
                    _optional_string(metadata.get("source")),
                    _optional_string(metadata.get("document_hash")),
                    str(metadata.get("status") or READY).upper(),
                    int(metadata.get("chunk_count") or 0),
                    _optional_string(metadata.get("owner_token")),
                    json.dumps(extra_metadata, ensure_ascii=False, sort_keys=True),
                ),
            )
        return identifier

    def claim_document(
        self,
        metadata: dict[str, Any],
        *,
        document_hash: str,
        owner_token: str,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        """Atomically claim a new or failed document for ingestion.

        ``BEGIN IMMEDIATE`` makes the hash lookup and state transition a single
        cross-process SQLite operation. A READY or actively owned document is
        observed but never claimed by another manager.
        """

        if not document_hash.strip() or not owner_token.strip():
            raise ValueError("Document hash and owner token cannot be empty.")
        prepared = _prepare_metadata(metadata)
        identifier = document_id or str(uuid.uuid4())

        with self._database.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM documents WHERE document_hash = ?",
                (document_hash,),
            ).fetchone()

            if row is None:
                connection.execute(
                    """
                    INSERT INTO documents (
                        id, filename, document_type, author, date_added, tags,
                        source, document_hash, status, chunk_count, owner_token,
                        extra_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        identifier,
                        prepared["filename"],
                        prepared["document_type"],
                        prepared["author"],
                        prepared["date_added"],
                        prepared["tags"],
                        prepared["source"],
                        document_hash,
                        PENDING,
                        0,
                        owner_token,
                        prepared["extra_metadata"],
                    ),
                )
                connection.execute(
                    "UPDATE documents SET status = ? WHERE id = ? AND owner_token = ?",
                    (PROCESSING, identifier, owner_token),
                )
                row = connection.execute(
                    "SELECT * FROM documents WHERE id = ?",
                    (identifier,),
                ).fetchone()
                return {
                    "owned": True,
                    "state": PROCESSING,
                    "previous_state": None,
                    "record": self._row_to_dict(row),
                }

            existing = self._row_to_dict(row)
            state = str(existing.get("status") or READY).upper()
            if state == FAILED:
                cursor = connection.execute(
                    """
                    UPDATE documents
                    SET filename = ?, document_type = ?, author = ?,
                        date_added = ?, tags = ?, source = ?, status = ?,
                        chunk_count = 0, owner_token = ?, extra_metadata = ?
                    WHERE id = ? AND status = ?
                    """,
                    (
                        prepared["filename"],
                        prepared["document_type"],
                        prepared["author"],
                        prepared["date_added"],
                        prepared["tags"],
                        prepared["source"],
                        PROCESSING,
                        owner_token,
                        prepared["extra_metadata"],
                        existing["id"],
                        FAILED,
                    ),
                )
                if cursor.rowcount == 1:
                    row = connection.execute(
                        "SELECT * FROM documents WHERE id = ?",
                        (existing["id"],),
                    ).fetchone()
                    return {
                        "owned": True,
                        "state": PROCESSING,
                        "previous_state": FAILED,
                        "record": self._row_to_dict(row),
                    }

            visible_state = READY if state == READY else PROCESSING
            return {
                "owned": False,
                "state": visible_state,
                "previous_state": state,
                "record": existing,
            }

    def update_owned_document(
        self,
        document_id: str,
        owner_token: str,
        metadata: dict[str, Any],
    ) -> bool:
        """Update catalog metadata only for the active ingestion owner."""

        prepared = _prepare_metadata(metadata)
        with self._database.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE documents
                SET filename = ?, document_type = ?, author = ?, tags = ?,
                    source = ?, extra_metadata = ?
                WHERE id = ? AND status = ? AND owner_token = ?
                """,
                (
                    prepared["filename"],
                    prepared["document_type"],
                    prepared["author"],
                    prepared["tags"],
                    prepared["source"],
                    prepared["extra_metadata"],
                    document_id,
                    PROCESSING,
                    owner_token,
                ),
            )
        return cursor.rowcount == 1

    def reclaim_inconsistent_ready_document(
        self,
        document_id: str,
        owner_token: str,
    ) -> bool:
        """Atomically give one manager ownership of an inconsistent READY row."""

        with self._database.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE documents
                SET status = ?, chunk_count = 0, owner_token = ?
                WHERE id = ? AND status = ?
                """,
                (PROCESSING, owner_token, document_id, READY),
            )
        return cursor.rowcount == 1

    def update_owned_chunk_count(
        self,
        document_id: str,
        owner_token: str,
        chunk_count: int,
    ) -> bool:
        with self._database.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE documents SET chunk_count = ?
                WHERE id = ? AND status = ? AND owner_token = ?
                """,
                (int(chunk_count), document_id, PROCESSING, owner_token),
            )
        return cursor.rowcount == 1

    def finish_ingestion(
        self,
        document_id: str,
        owner_token: str,
        state: str,
    ) -> bool:
        """Transition the active owner's document to READY or FAILED."""

        target = state.upper()
        if target not in {READY, FAILED}:
            raise ValueError("Ingestion can finish only as READY or FAILED.")
        with self._database.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE documents
                SET status = ?,
                    chunk_count = CASE WHEN ? = ? THEN 0 ELSE chunk_count END,
                    owner_token = NULL
                WHERE id = ? AND status = ? AND owner_token = ?
                """,
                (target, target, FAILED, document_id, PROCESSING, owner_token),
            )
        return cursor.rowcount == 1

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def get_document_by_hash(self, document_hash: str) -> dict[str, Any] | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE document_hash = ?",
                (document_hash,),
            ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def list_documents(self) -> list[dict[str, Any]]:
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM documents ORDER BY date_added DESC, id DESC"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def update_document_state(
        self,
        document_id: str,
        *,
        status: str | None = None,
        chunk_count: int | None = None,
    ) -> bool:
        assignments: list[str] = []
        values: list[Any] = []
        if status is not None:
            assignments.append("status = ?")
            values.append(status.upper())
        if chunk_count is not None:
            assignments.append("chunk_count = ?")
            values.append(int(chunk_count))
        if not assignments:
            return self.get_document(document_id) is not None
        values.append(document_id)
        with self._database.connection() as connection:
            cursor = connection.execute(
                f"UPDATE documents SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
        return cursor.rowcount > 0

    def delete_document(self, document_id: str) -> bool:
        with self._database.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,),
            )
        return cursor.rowcount > 0

    def count(self) -> int:
        with self._database.connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
        return int(row["count"])

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        raw = dict(row)
        raw.pop("owner_token", None)
        extra = json.loads(raw.pop("extra_metadata", "{}") or "{}")
        extra.update(raw)
        extra["tags"] = json.loads(extra["tags"] or "[]")
        return extra

    def close(self) -> None:
        self._database.close()

    def __enter__(self) -> "MetadataStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _prepare_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    filename = str(metadata.get("filename", "")).strip()
    document_type = str(metadata.get("document_type", "")).strip().lower()
    if not filename or not document_type:
        raise ValueError("Metadata requires filename and document_type.")
    tags = metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    extra_metadata = {
        key: value for key, value in metadata.items() if key not in _CORE_FIELDS
    }
    return {
        "filename": filename,
        "document_type": document_type,
        "author": _optional_string(metadata.get("author")),
        "date_added": str(
            metadata.get("date_added") or datetime.now(timezone.utc).isoformat()
        ),
        "tags": json.dumps(normalized_tags, ensure_ascii=False),
        "source": _optional_string(metadata.get("source")),
        "extra_metadata": json.dumps(
            extra_metadata,
            ensure_ascii=False,
            sort_keys=True,
        ),
    }
