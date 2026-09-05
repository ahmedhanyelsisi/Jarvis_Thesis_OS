from .exceptions import RevisionLimitError
from .chapter_manager import ChapterManager
from .models import ChapterState

class RevisionEngine:
    """Safeguards the draft-review loop."""
    
    MAX_REVISION_ITERATIONS = 3
    
    def __init__(self, chapter_manager: ChapterManager):
        self._chapters = chapter_manager

    def request_revision(self, chapter_id: str):
        """Called when quality scores fail threshold."""
        count = self._chapters.increment_revision(chapter_id)
        if count >= self.MAX_REVISION_ITERATIONS:
            raise RevisionLimitError(
                f"Chapter {chapter_id} reached max revisions ({self.MAX_REVISION_ITERATIONS}). "
                "Halting pipeline for human intervention."
            )
        self._chapters.update_state(chapter_id, ChapterState.NEEDS_REVISION)

    def mark_approved(self, chapter_id: str):
        """Called when quality scores pass threshold."""
        self._chapters.update_state(chapter_id, ChapterState.APPROVED)
