"""Read-only adapter around the unchanged Stone 10 workspace API."""
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path, PureWindowsPath
from conversation_core.service_models import PreparedAction
from thesis_workspace import ThesisWorkspaceManager


_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _validate_root_input(value):
    """Reject Windows root spellings whose target cannot be safely pinned."""
    windows = PureWindowsPath(str(value))
    if windows.drive.startswith("\\\\"):
        raise ValueError("UNC thesis roots are not accepted by the voice inspector")
    if windows.drive and not windows.is_absolute():
        raise ValueError("Drive-relative thesis roots are not accepted by the voice inspector")


def _is_reparse_point(path):
    """Detect links even when pathlib lacks a reparse-point helper."""
    metadata = path.lstat()
    return (path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())
            or bool(getattr(metadata, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT))


class WorkspaceBackend:
    CAPABILITIES = {"thesis.inspect": "Inspect LaTeX structure and citations"}

    def __init__(self, thesis_root, *, platform_root=None, max_files=1000, max_bytes=20_000_000):
        _validate_root_input(thesis_root)
        raw_root = Path(thesis_root).expanduser()
        if _is_reparse_point(raw_root):
            raise ValueError("Linked thesis roots are not accepted by the voice inspector")
        self.root = raw_root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("The thesis root must be a directory")
        if platform_root:
            platform = Path(platform_root).resolve(strict=True)
            if self.root == platform or self.root in platform.parents or platform in self.root.parents:
                raise ValueError("Thesis and platform roots must be separate")
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.__manager = ThesisWorkspaceManager(self.root)

    def _fingerprint(self):
        if not self.root.is_dir() or self.root.resolve() != self.root:
            raise ValueError("Thesis root changed")
        digest = hashlib.sha256()
        count = total = 0
        for current, directories, names in os.walk(self.root, followlinks=False):
            directories[:] = sorted(d for d in directories if not d.startswith(".") and d != "__pycache__")
            for name in list(directories) + names:
                count += 1
                if count > self.max_files:
                    raise ValueError("Workspace file/directory limit exceeded")
                candidate = Path(current) / name
                if _is_reparse_point(candidate):
                    raise ValueError("Linked files/directories are not accepted by the voice inspector")
                resolved = candidate.resolve(strict=True)
                try:
                    contained = os.path.commonpath((os.path.normcase(str(self.root)),
                                                     os.path.normcase(str(resolved)))) == os.path.normcase(str(self.root))
                except ValueError:
                    contained = False
                if not contained:
                    raise ValueError("Workspace path escapes the configured root")
            for name in sorted(names):
                path = Path(current) / name
                if path.suffix.lower() not in (".tex", ".bib"):
                    continue
                size = path.stat().st_size
                total += size
                if total > self.max_bytes:
                    raise ValueError("Workspace text size limit exceeded")
                digest.update(path.relative_to(self.root).as_posix().encode())
                digest.update(b"\0")
                with path.open("rb") as stream:
                    content = stream.read(self.max_bytes + 1)
                if len(content) != size:
                    raise ValueError("Workspace changed during inspection")
                digest.update(content)
        return digest.hexdigest()

    def prepare(self, capability, payload=None):
        if capability not in self.CAPABILITIES or payload not in (None, {}):
            raise ValueError("Capability or target parameters are not supported")
        return PreparedAction(capability, "WorkspaceInspector", "review", str(self.root),
                              self._fingerprint(), "READ", "thesis_workspace")

    def current_binding(self, action):
        return str(self.root), self._fingerprint()

    def execute(self, action, *, cancel_event=None):
        if action.capability not in self.CAPABILITIES or action.target != str(self.root) or action.payload_json != "{}":
            raise ValueError("Invalid backend action")
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Inspection cancelled")
        if self._fingerprint() != action.source_version:
            raise ValueError("Thesis changed; request a fresh inspection")
        structure = self.__manager.discover()
        citations = self.__manager.check_citations(structure)
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Inspection cancelled")
        if self._fingerprint() != action.source_version:
            raise ValueError("Thesis changed during inspection; result discarded")
        result = {"tex_files": list(structure.tex_files), "bibliography_files": list(structure.bibliography_files),
                  "chapters": [asdict(c) for d in structure.documents for c in d.chapters],
                  "citations": asdict(citations), "source_version": action.source_version,
                  "read_only": True}
        missing = [issue.key for issue in citations.missing_bibliography_entries]
        result["summary"] = (f"Inspected {len(structure.tex_files)} LaTeX files. "
                             f"Found {len(missing)} missing bibliography entries. "
                             + ("Missing: " + ", ".join(missing[:5]) + "." if missing else ""))
        return result
