import os
from pathlib import Path
from typing import Optional

from thesis_workspace.file_operations import SafeFileOperations
from .exceptions import PathViolationError

class SafeAgentFileAccess:
    """
    Sandboxed file I/O layer for AI agents.
    Wraps thesis_workspace.SafeFileOperations with aggressive path validation.
    Agents can only read and write within the thesis_root.
    Cannot delete, move, or chmod.
    """
    def __init__(self, thesis_root: str | Path):
        self._root = Path(thesis_root).resolve()
        self._ops = SafeFileOperations(self._root)
        
    def _validate_path(self, target_path: str) -> Path:
        """Ensure the target path is strictly inside thesis_root."""
        if not isinstance(target_path, str):
            raise TypeError("Path must be a string")
        if "\x00" in target_path:
            raise PathViolationError("Null byte injection detected in path")
            
        p = Path(target_path)
        if p.is_absolute():
            raise PathViolationError(f"Absolute paths forbidden: {target_path}")
            
        resolved = (self._root / p).resolve()
        
        try:
            # Verify the resolved path is a subpath of root
            resolved.relative_to(self._root)
            return resolved
        except ValueError as e:
            raise PathViolationError(f"Path traversal blocked: {target_path}") from e

    def read_file(self, relative_path: str) -> str:
        """Read a file within the thesis workspace."""
        safe_path = self._validate_path(relative_path)
        if not safe_path.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return safe_path.read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> None:
        """Write content to a file within the thesis workspace. Can create new files."""
        # Validate path (raises PathViolationError if unsafe)
        safe_path = self._validate_path(relative_path)
        
        # We use SafeFileOperations to perform the atomic, safe write
        proposal = self._ops.create_proposal(relative_path, content)
        self._ops.apply(proposal, confirmed=True)
