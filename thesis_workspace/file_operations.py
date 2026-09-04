"""Confirmation-gated and root-confined thesis file modifications."""

from __future__ import annotations

import difflib
import hashlib
import os
import stat
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .document_models import ChangeAnalysis, ProposedModification


class WorkspaceLockError(RuntimeError):
    """Raised when the workspace write lock cannot be acquired safely."""


_THREAD_LOCKS: dict[Path, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


class SafeFileOperations:
    """Analyze and propose changes without writing until explicitly approved."""

    def __init__(self, root: str | Path, *, lock_timeout: float = 10.0) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"Workspace does not exist: {self.root}")
        if isinstance(lock_timeout, bool) or not isinstance(lock_timeout, (int, float)):
            raise TypeError("lock_timeout must be a number.")
        if lock_timeout < 0:
            raise ValueError("lock_timeout cannot be negative.")
        self.lock_timeout = float(lock_timeout)
        with _THREAD_LOCKS_GUARD:
            self._thread_lock = _THREAD_LOCKS.setdefault(self.root, threading.Lock())

    def analyze_change(self, path: str | Path, content: str) -> ChangeAnalysis:
        if not isinstance(content, str):
            raise TypeError("Proposed file content must be a string.")
        target = self._resolve(path)
        if target.exists() and not target.is_file():
            raise IsADirectoryError(f"Modification target is not a file: {target}")
        exists = target.is_file()
        old_content = target.read_text(encoding="utf-8") if exists else ""
        relative_path = target.relative_to(self.root).as_posix()
        diff = "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{relative_path}" if exists else "/dev/null",
                tofile=f"b/{relative_path}",
            )
        )
        return ChangeAnalysis(
            path=relative_path,
            exists=exists,
            changed=not exists or old_content != content,
            old_digest=self._digest(old_content) if exists else None,
            new_digest=self._digest(content),
            diff=diff,
        )

    def create_proposal(self, path: str | Path, content: str) -> ProposedModification:
        analysis = self.analyze_change(path, content)
        return ProposedModification(
            proposal_id=self._proposal_id(analysis),
            analysis=analysis,
            content=content,
        )

    propose_change = create_proposal

    def apply(self, proposal: ProposedModification, *, confirmed: bool = False) -> Path:
        if confirmed is not True:
            raise PermissionError("Explicit confirmation is required before writing.")
        if not isinstance(proposal, ProposedModification):
            raise TypeError("apply() requires a ProposedModification.")
        if proposal.proposal_id != self._proposal_id(proposal.analysis):
            raise ValueError("The proposal identifier does not match its analysis.")

        target = self._resolve(proposal.analysis.path)
        with self._workspace_lock():
            current_exists = self._verify_current_state(target, proposal.analysis)
            if self._digest(proposal.content) != proposal.analysis.new_digest:
                raise ValueError("The proposed content does not match its recorded digest.")
            expected_changed = not proposal.analysis.exists or (
                proposal.analysis.old_digest != proposal.analysis.new_digest
            )
            if proposal.analysis.changed != expected_changed:
                raise ValueError("The proposal change state is inconsistent with its digests.")
            if not proposal.analysis.changed:
                return target

            target.parent.mkdir(parents=True, exist_ok=True)
            existing_mode = stat.S_IMODE(target.stat().st_mode) if current_exists else None
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                    stream.write(proposal.content)
                    stream.flush()
                    os.fsync(stream.fileno())
                if existing_mode is not None:
                    os.chmod(temporary_name, existing_mode)
                self._verify_current_state(target, proposal.analysis)
                os.replace(temporary_name, target)
            except BaseException:
                Path(temporary_name).unlink(missing_ok=True)
                raise
        return target

    apply_proposal = apply

    def _resolve(self, path: str | Path) -> Path:
        if not isinstance(path, (str, Path)):
            raise TypeError("File path must be a string or Path.")
        raw_path = os.fspath(path)
        if not raw_path.strip() or "\x00" in raw_path:
            raise ValueError("File path cannot be empty or contain null bytes.")
        candidate = Path(path)
        if ".." in candidate.parts:
            raise ValueError("Paths must remain inside the workspace; parent traversal is not allowed.")
        target = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        if target == self.root:
            raise ValueError("The workspace root is not a valid file target.")
        try:
            target.relative_to(self.root)
        except ValueError as error:
            raise ValueError("File operations must remain inside the thesis workspace.") from error
        return target

    @staticmethod
    def _digest(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _proposal_id(analysis: ChangeAnalysis) -> str:
        identity = (
            f"{analysis.path}\0{analysis.exists}\0{analysis.changed}\0"
            f"{analysis.old_digest}\0{analysis.new_digest}\0{analysis.diff}"
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]

    def _verify_current_state(self, target: Path, analysis: ChangeAnalysis) -> bool:
        if target.exists() and not target.is_file():
            raise RuntimeError("The target is no longer a regular file.")
        current_exists = target.is_file()
        current_content = target.read_text(encoding="utf-8") if current_exists else ""
        current_digest = self._digest(current_content) if current_exists else None
        if current_exists != analysis.exists or current_digest != analysis.old_digest:
            raise RuntimeError(
                "The target changed after this proposal was created; analyze it again."
            )
        return current_exists

    @contextmanager
    def _workspace_lock(self) -> Iterator[None]:
        deadline = time.monotonic() + self.lock_timeout
        if not self._thread_lock.acquire(timeout=self.lock_timeout):
            raise WorkspaceLockError("Timed out waiting for the workspace write lock.")

        stream = None
        locked = False
        try:
            try:
                lock_path = self.root / ".jarvis-thesis-workspace.lock"
                if lock_path.is_symlink():
                    raise WorkspaceLockError(
                        "The workspace lock path cannot be a symbolic link."
                    )
                flags = os.O_CREAT | os.O_RDWR
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                descriptor = os.open(lock_path, flags, 0o600)
                try:
                    stream = os.fdopen(descriptor, "r+b", buffering=0)
                except BaseException:
                    os.close(descriptor)
                    raise
                if os.fstat(stream.fileno()).st_size == 0:
                    stream.write(b"\0")
                    stream.flush()
                    os.fsync(stream.fileno())
                self._acquire_os_lock(stream, deadline)
                locked = True
            except OSError as error:
                raise WorkspaceLockError(
                    "Unable to acquire the workspace write lock."
                ) from error
            yield
        finally:
            try:
                if stream is not None:
                    if locked:
                        self._release_os_lock(stream)
                    try:
                        stream.close()
                    except OSError:
                        pass
            finally:
                self._thread_lock.release()

    @staticmethod
    def _acquire_os_lock(stream, deadline: float) -> None:
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise WorkspaceLockError(
                        "Timed out waiting for the workspace write lock."
                    ) from error
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

    @staticmethod
    def _release_os_lock(stream) -> None:
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        except OSError:
            # Closing the file descriptor also releases OS-level advisory locks.
            pass
