"""Per-chapter lifecycle state machine for the Stone 12 orchestration layer.

Enforces deterministic stage transitions. In-process state only — not
persisted by Stone 12. The Kernel may serialize snapshots to Stone 6
at its discretion.
"""

from __future__ import annotations

from threading import RLock

from .models import ChapterLifecycle, StageTransition, ThesisStage, utc_now


class InvalidTransitionError(ValueError):
    """Raised when a lifecycle stage transition violates state machine rules."""


# Valid transitions: from_stage -> frozenset of allowed target stages.
_VALID_TRANSITIONS: dict[ThesisStage, frozenset[ThesisStage]] = {
    ThesisStage.PLANNING: frozenset({ThesisStage.DRAFTING}),
    ThesisStage.DRAFTING: frozenset({ThesisStage.ANALYSIS}),
    ThesisStage.ANALYSIS: frozenset({ThesisStage.REVISION, ThesisStage.REVIEW}),
    ThesisStage.REVISION: frozenset({ThesisStage.ANALYSIS}),
    ThesisStage.REVIEW: frozenset({ThesisStage.FINALIZATION, ThesisStage.REVISION}),
    ThesisStage.FINALIZATION: frozenset({ThesisStage.COMPLETE}),
    ThesisStage.COMPLETE: frozenset(),
}


class LifecycleManager:
    """Track and enforce per-chapter lifecycle stage transitions.

    In-process state only — not persisted by Stone 12.
    The Kernel may serialize snapshots to Stone 6 at its discretion.
    """

    def __init__(self) -> None:
        self._chapters: dict[str, ChapterLifecycle] = {}
        self._lock = RLock()

    def get(self, chapter: str) -> ChapterLifecycle:
        """Return the lifecycle for *chapter*, creating it at PLANNING if new."""

        with self._lock:
            if chapter not in self._chapters:
                self._chapters[chapter] = ChapterLifecycle(
                    chapter=chapter,
                    stage=ThesisStage.PLANNING,
                )
            return self._chapters[chapter]

    def advance(
        self,
        chapter: str,
        target_stage: ThesisStage,
        reason: str = "",
    ) -> ChapterLifecycle:
        """Transition *chapter* to *target_stage* if the transition is valid."""

        with self._lock:
            current = self.get(chapter)
            allowed = _VALID_TRANSITIONS.get(current.stage, frozenset())

            if target_stage not in allowed:
                raise InvalidTransitionError(
                    f"Cannot transition chapter {chapter!r} from "
                    f"{current.stage.value!r} to {target_stage.value!r}. "
                    f"Allowed targets: "
                    f"{sorted(s.value for s in allowed)}."
                )

            transition = StageTransition(
                from_stage=current.stage,
                to_stage=target_stage,
                timestamp=utc_now(),
                reason=reason,
            )

            updated = ChapterLifecycle(
                chapter=chapter,
                stage=target_stage,
                history=current.history + (transition,),
            )

            self._chapters[chapter] = updated
            return updated

    def list_all(self) -> tuple[ChapterLifecycle, ...]:
        """Return lifecycle states for all tracked chapters, sorted by name."""

        with self._lock:
            return tuple(
                self._chapters[k]
                for k in sorted(self._chapters)
            )
