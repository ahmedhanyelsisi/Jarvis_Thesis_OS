from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum

class ThesisLifecycleState(Enum):
    INIT = "INIT"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    DRAFTING = "DRAFTING"
    REVIEWING = "REVIEWING"
    REVISING = "REVISING"
    ASSEMBLING = "ASSEMBLING"
    PUBLISHED = "PUBLISHED"
    PAUSED_FOR_APPROVAL = "PAUSED_FOR_APPROVAL"

class ChapterState(Enum):
    NOT_STARTED = "NOT_STARTED"
    DRAFTING = "DRAFTING"
    NEEDS_REVISION = "NEEDS_REVISION"
    APPROVED = "APPROVED"

@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    target_state: str
    context: str
    secure_token: str

@dataclass(frozen=True)
class ChapterDependency:
    chapter_id: str
    depends_on: Tuple[str, ...]

@dataclass(frozen=True)
class ChapterStatus:
    chapter_id: str
    state: ChapterState
    revision_count: int

@dataclass(frozen=True)
class PipelineState:
    session_id: str
    current_state: ThesisLifecycleState
    chapters: Tuple[ChapterStatus, ...]
    dependencies: Tuple[ChapterDependency, ...]
