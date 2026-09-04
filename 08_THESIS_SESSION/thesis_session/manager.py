import json
import uuid
import time
import os
from pathlib import Path
from dataclasses import replace

from jarvis_core.interfaces import IEventBus
from .models import ThesisSession, ChapterState, ChapterStatus, SessionSnapshot
from .exceptions import SessionPersistenceError, SessionError

class ThesisSessionManager:
    """Stateful coordinator for the thesis session."""
    
    def __init__(self, event_bus: IEventBus, thesis_root: str | Path):
        self._event_bus = event_bus
        self._root = Path(thesis_root).resolve()
        self._jarvis_dir = self._root / ".jarvis"
        self._session_file = self._jarvis_dir / "session.json"
        
        # In-memory immutable state
        self._session: ThesisSession | None = None
        
        # Load from disk if exists, otherwise create
        self._load_or_create()

    def _load_or_create(self) -> None:
        """Load session snapshot from disk, or start a new one."""
        self._jarvis_dir.mkdir(parents=True, exist_ok=True)
        if self._session_file.exists():
            try:
                data = json.loads(self._session_file.read_text(encoding="utf-8"))
                # Restore the basic state
                # Note: For this Stone, we re-hydrate a minimal runtime representation
                # We initialize ChapterState based on the chapter_names
                chapters = tuple(ChapterState(chapter_name=c, file_path=f"{c}.tex") for c in data.get("chapter_names", []))
                
                self._session = ThesisSession(
                    session_id=data["session_id"],
                    thesis_root=data["thesis_root"],
                    active_chapter=data.get("active_chapter"),
                    chapters=chapters,
                    build_task_ids=tuple(["dummy"] * data.get("build_count", 0)),
                    review_summaries=tuple(["dummy"] * data.get("review_count", 0)),
                    created_at=data["created_at"],
                    updated_at=data["updated_at"]
                )
            except Exception as e:
                # If corrupt, overwrite with new
                self._create_new()
        else:
            self._create_new()

    def _create_new(self) -> None:
        self._session = ThesisSession(
            session_id=str(uuid.uuid4()),
            thesis_root=str(self._root)
        )
        self._save()
        self._safe_publish("session.created", {"session_id": self._session.session_id})

    def _save(self) -> None:
        """Persist snapshot to disk."""
        if not self._session:
            return
        snapshot = SessionSnapshot.from_session(self._session)
        try:
            self._session_file.write_text(
                json.dumps(snapshot.__dict__, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            raise SessionPersistenceError(f"Failed to persist session: {str(e)}") from e

    def _safe_publish(self, event_name: str, payload: dict) -> None:
        try:
            self._event_bus.publish(event_name, payload)
        except Exception:
            pass

    def get_session(self) -> ThesisSession:
        if not self._session:
            raise SessionError("No active session.")
        return self._session

    def set_active_chapter(self, chapter_name: str) -> ThesisSession:
        """Change the active chapter and emit event."""
        if not self._session:
            raise SessionError("No active session.")
            
        current = self._session
        
        # Ensure chapter exists in state
        chapters = list(current.chapters)
        if not any(c.chapter_name == chapter_name for c in chapters):
            chapters.append(ChapterState(chapter_name=chapter_name, file_path=f"{chapter_name}.tex"))
            
        new_session = replace(
            current,
            active_chapter=chapter_name,
            chapters=tuple(chapters),
            updated_at=time.time()
        )
        self._session = new_session
        self._save()
        self._safe_publish("session.chapter.changed", {
            "session_id": self._session.session_id,
            "active_chapter": chapter_name
        })
        return self._session

    def record_build(self, task_id: str) -> ThesisSession:
        """Record a build task completion."""
        if not self._session:
            raise SessionError("No active session.")
            
        new_session = replace(
            self._session,
            build_task_ids=self._session.build_task_ids + (task_id,),
            updated_at=time.time()
        )
        self._session = new_session
        self._save()
        self._safe_publish("session.build.recorded", {
            "session_id": self._session.session_id,
            "task_id": task_id
        })
        return self._session
        
    def record_review(self, summary: str) -> ThesisSession:
        """Record a chapter review."""
        if not self._session:
            raise SessionError("No active session.")
            
        new_session = replace(
            self._session,
            review_summaries=self._session.review_summaries + (summary,),
            updated_at=time.time()
        )
        self._session = new_session
        self._save()
        self._safe_publish("session.review.recorded", {
            "session_id": self._session.session_id,
            "summary_length": len(summary)
        })
        return self._session
