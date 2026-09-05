from typing import Dict, List, Tuple
from .models import ChapterStatus, ChapterState, ChapterDependency
from .exceptions import ChapterDependencyError

class ChapterManager:
    """Tracks chapter progress and dependency integrity."""
    
    def __init__(self):
        self._statuses: Dict[str, ChapterStatus] = {}
        self._dependencies: Dict[str, ChapterDependency] = {}

    def register_chapter(self, chapter_id: str, depends_on: List[str] = None):
        depends_on = depends_on or []
        self._statuses[chapter_id] = ChapterStatus(chapter_id, ChapterState.NOT_STARTED, 0)
        self._dependencies[chapter_id] = ChapterDependency(chapter_id, tuple(depends_on))

    def get_status(self, chapter_id: str) -> ChapterStatus:
        if chapter_id not in self._statuses:
            raise KeyError(f"Chapter {chapter_id} not found.")
        return self._statuses[chapter_id]

    def update_state(self, chapter_id: str, new_state: ChapterState):
        current = self.get_status(chapter_id)
        
        # Enforce dependencies: Cannot draft if dependencies are not APPROVED
        if new_state == ChapterState.DRAFTING:
            deps = self._dependencies[chapter_id].depends_on
            for dep_id in deps:
                dep_status = self.get_status(dep_id)
                if dep_status.state != ChapterState.APPROVED:
                    raise ChapterDependencyError(f"Cannot draft {chapter_id}. Dependency {dep_id} is not APPROVED.")
                    
        self._statuses[chapter_id] = ChapterStatus(chapter_id, new_state, current.revision_count)

    def increment_revision(self, chapter_id: str) -> int:
        current = self.get_status(chapter_id)
        new_count = current.revision_count + 1
        self._statuses[chapter_id] = ChapterStatus(chapter_id, current.state, new_count)
        return new_count

    def get_all_statuses(self) -> Tuple[ChapterStatus, ...]:
        return tuple(self._statuses.values())

    def get_all_dependencies(self) -> Tuple[ChapterDependency, ...]:
        return tuple(self._dependencies.values())
