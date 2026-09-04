"""Immutable data models for the Stone 10 thesis workspace layer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, TypeVar


_T = TypeVar("_T")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_PROPOSAL_ID = re.compile(r"[0-9a-f]{20}")


def _required_text(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} cannot be empty.")
    return normalized


def _typed_tuple(values: Iterable[_T], expected_type: type[_T], name: str) -> tuple[_T, ...]:
    try:
        normalized = tuple(values)
    except TypeError as error:
        raise TypeError(f"{name} must be an iterable.") from error
    if any(not isinstance(value, expected_type) for value in normalized):
        raise TypeError(f"Every item in {name} must be {expected_type.__name__}.")
    return normalized


def _relative_path(value: str, name: str) -> str:
    normalized = _required_text(value, name).replace("\\", "/")
    path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(normalized)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or normalized == "."
        or ".." in path.parts
    ):
        raise ValueError(f"{name} must be a workspace-relative path.")
    return path.as_posix()


@dataclass(frozen=True, order=True)
class SourceLocation:
    """Location of a LaTeX construct in a workspace-relative source file."""

    path: str
    line: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _required_text(self.path, "path"))
        if isinstance(self.line, bool) or not isinstance(self.line, int):
            raise TypeError("line must be an integer.")
        if self.line < 1:
            raise ValueError("line must be positive.")


@dataclass(frozen=True)
class DocumentElement:
    """A named LaTeX construct and its source location."""

    value: str
    location: SourceLocation

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _required_text(self.value, "value"))
        if not isinstance(self.location, SourceLocation):
            raise TypeError("location must be a SourceLocation.")


@dataclass(frozen=True)
class FigureElement:
    """A figure environment or included graphic found in a document."""

    path: str | None
    caption: str | None
    label: str | None
    location: SourceLocation

    def __post_init__(self) -> None:
        for name in ("path", "caption", "label"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required_text(value, name))
        if not isinstance(self.location, SourceLocation):
            raise TypeError("location must be a SourceLocation.")


@dataclass(frozen=True)
class LatexEnvironment:
    """A supported non-figure LaTeX environment."""

    name: str
    label: str | None
    location: SourceLocation

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "name").lower())
        if self.label is not None:
            object.__setattr__(self, "label", _required_text(self.label, "label"))
        if not isinstance(self.location, SourceLocation):
            raise TypeError("location must be a SourceLocation.")


@dataclass(frozen=True, order=True)
class ParseDiagnostic:
    """Non-fatal syntax or consistency problem found during LaTeX parsing."""

    code: str
    message: str
    location: SourceLocation

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_text(self.code, "code"))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        if not isinstance(self.location, SourceLocation):
            raise TypeError("location must be a SourceLocation.")


@dataclass(frozen=True)
class LatexDocument:
    """Deterministic parse result for one LaTeX source file."""

    path: str
    chapters: tuple[DocumentElement, ...] = ()
    sections: tuple[DocumentElement, ...] = ()
    citations: tuple[DocumentElement, ...] = ()
    references: tuple[DocumentElement, ...] = ()
    labels: tuple[DocumentElement, ...] = ()
    figures: tuple[FigureElement, ...] = ()
    diagnostics: tuple[ParseDiagnostic, ...] = ()
    environments: tuple[LatexEnvironment, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _required_text(self.path, "path"))
        for name in ("chapters", "sections", "citations", "references", "labels"):
            object.__setattr__(
                self,
                name,
                _typed_tuple(getattr(self, name), DocumentElement, name),
            )
        object.__setattr__(self, "figures", _typed_tuple(self.figures, FigureElement, "figures"))
        object.__setattr__(
            self,
            "environments",
            _typed_tuple(self.environments, LatexEnvironment, "environments"),
        )
        diagnostics = _typed_tuple(self.diagnostics, ParseDiagnostic, "diagnostics")
        object.__setattr__(self, "diagnostics", tuple(sorted(diagnostics)))


@dataclass(frozen=True)
class ThesisStructure:
    """Stable, serializable snapshot of a thesis directory."""

    root: Path
    tex_files: tuple[str, ...]
    bibliography_files: tuple[str, ...]
    figure_files: tuple[str, ...]
    documents: tuple[LatexDocument, ...]

    def __post_init__(self) -> None:
        root = Path(self.root).resolve()
        object.__setattr__(self, "root", root)
        for name in ("tex_files", "bibliography_files", "figure_files"):
            paths = tuple(_relative_path(value, name) for value in getattr(self, name))
            object.__setattr__(self, name, tuple(sorted(set(paths))))
        documents = _typed_tuple(self.documents, LatexDocument, "documents")
        object.__setattr__(self, "documents", tuple(sorted(documents, key=lambda item: item.path)))
        document_paths = {document.path for document in documents}
        if len(document_paths) != len(documents):
            raise ValueError("Parsed document paths must be unique.")
        unknown_documents = document_paths.difference(self.tex_files)
        if unknown_documents:
            raise ValueError("Every parsed document must correspond to a discovered .tex file.")

    @property
    def duplicate_labels(self) -> tuple[DocumentElement, ...]:
        """Return repeated label definitions after their first occurrence."""

        seen: set[str] = set()
        duplicates: list[DocumentElement] = []
        for document in self.documents:
            for label in document.labels:
                if label.value in seen:
                    duplicates.append(label)
                seen.add(label.value)
        return tuple(duplicates)

    @property
    def unresolved_references(self) -> tuple[DocumentElement, ...]:
        """Return cross-references without a label anywhere in the workspace."""

        labels = {
            label.value
            for document in self.documents
            for label in document.labels
        }
        return tuple(
            reference
            for document in self.documents
            for reference in document.references
            if reference.value not in labels
        )


@dataclass(frozen=True)
class CitationIssue:
    """A citation problem with optional definition/use locations."""

    key: str
    locations: tuple[SourceLocation, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _required_text(self.key, "key"))
        locations = _typed_tuple(self.locations, SourceLocation, "locations")
        object.__setattr__(self, "locations", tuple(sorted(locations)))


@dataclass(frozen=True)
class CitationReport:
    """Citation consistency result for a complete workspace."""

    missing_bibliography_entries: tuple[CitationIssue, ...] = ()
    unused_bibliography_entries: tuple[CitationIssue, ...] = ()
    duplicate_citation_keys: tuple[CitationIssue, ...] = ()
    missing_bibliography_files: tuple[str, ...] = ()
    malformed_bibliography_entries: tuple[SourceLocation, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "missing_bibliography_entries",
            "unused_bibliography_entries",
            "duplicate_citation_keys",
        ):
            issues = _typed_tuple(getattr(self, name), CitationIssue, name)
            object.__setattr__(self, name, tuple(sorted(issues, key=lambda item: item.key)))
        missing_files = tuple(
            _required_text(path, "missing bibliography path")
            for path in self.missing_bibliography_files
        )
        object.__setattr__(self, "missing_bibliography_files", tuple(sorted(set(missing_files))))
        malformed = _typed_tuple(
            self.malformed_bibliography_entries,
            SourceLocation,
            "malformed_bibliography_entries",
        )
        object.__setattr__(self, "malformed_bibliography_entries", tuple(sorted(malformed)))

    @property
    def unused_citations(self) -> tuple[CitationIssue, ...]:
        """Compatibility name for bibliography entries that are never cited."""

        return self.unused_bibliography_entries

    @property
    def is_valid(self) -> bool:
        return not (
            self.missing_bibliography_entries
            or self.duplicate_citation_keys
            or self.missing_bibliography_files
            or self.malformed_bibliography_entries
        )


@dataclass(frozen=True)
class ChangeAnalysis:
    """Read-only analysis of a proposed file replacement."""

    path: str
    exists: bool
    changed: bool
    old_digest: str | None
    new_digest: str
    diff: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _relative_path(self.path, "path"))
        if not isinstance(self.exists, bool) or not isinstance(self.changed, bool):
            raise TypeError("exists and changed must be booleans.")
        if self.old_digest is not None and not _DIGEST.fullmatch(self.old_digest):
            raise ValueError("old_digest must be a SHA-256 hexadecimal digest or None.")
        if not isinstance(self.new_digest, str) or not _DIGEST.fullmatch(self.new_digest):
            raise ValueError("new_digest must be a SHA-256 hexadecimal digest.")
        if not isinstance(self.diff, str):
            raise TypeError("diff must be a string.")
        if not self.exists and self.old_digest is not None:
            raise ValueError("A new target cannot have an old digest.")


@dataclass(frozen=True)
class ProposedModification:
    """An inert change proposal. Creating it never writes to disk."""

    proposal_id: str
    analysis: ChangeAnalysis
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.proposal_id, str) or not _PROPOSAL_ID.fullmatch(self.proposal_id):
            raise ValueError("proposal_id must be a 20-character hexadecimal identifier.")
        if not isinstance(self.analysis, ChangeAnalysis):
            raise TypeError("analysis must be a ChangeAnalysis.")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string.")
