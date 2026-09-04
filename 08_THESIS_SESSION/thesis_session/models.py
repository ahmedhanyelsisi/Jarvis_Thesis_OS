import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple
from pathlib import Path


class ChapterStatus(Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    COMPILED = "COMPILED"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class ChapterState:
    """Immutable snapshot of a single chapter's status."""
    chapter_name: str
    file_path: str
    word_count: int = 0
    status: ChapterStatus = ChapterStatus.DRAFT
    last_reviewed_at: Optional[float] = None
    last_compiled_at: Optional[float] = None


@dataclass(frozen=True)
class ThesisSession:
    """
    Immutable runtime representation of an active thesis work session.
    All state transitions produce new ThesisSession instances via dataclasses.replace().
    """
    session_id: str
    thesis_root: str                           # absolute path string for JSON safety
    active_chapter: Optional[str] = None
    chapters: Tuple[ChapterState, ...] = field(default_factory=tuple)
    build_task_ids: Tuple[str, ...] = field(default_factory=tuple)
    review_summaries: Tuple[str, ...] = field(default_factory=tuple)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SessionSnapshot:
    """
    Point-in-time serializable view of a ThesisSession.
    Used exclusively for disk persistence via .jarvis/session.json.
    """
    session_id: str
    thesis_root: str
    active_chapter: Optional[str]
    chapter_names: Tuple[str, ...]
    build_count: int
    review_count: int
    created_at: float
    updated_at: float

    @staticmethod
    def from_session(session: ThesisSession) -> "SessionSnapshot":
        return SessionSnapshot(
            session_id=session.session_id,
            thesis_root=session.thesis_root,
            active_chapter=session.active_chapter,
            chapter_names=tuple(c.chapter_name for c in session.chapters),
            build_count=len(session.build_task_ids),
            review_count=len(session.review_summaries),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
