"""Cross-check citations in LaTeX documents against BibTeX databases."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .document_models import CitationIssue, CitationReport, LatexDocument, SourceLocation


_BIB_ENTRY = re.compile(
    r"@\s*(?!comment\b|string\b|preamble\b)[A-Za-z]+\s*[{(]\s*([^,\s{}()]+)\s*,",
    re.IGNORECASE,
)
_BIB_START = re.compile(r"@\s*([A-Za-z]+)\s*([{(])", re.IGNORECASE)
_NON_ENTRY_TYPES = frozenset({"comment", "string", "preamble"})


class CitationChecker:
    """Perform deterministic, workspace-wide citation consistency checks."""

    def check(
        self,
        documents: Iterable[LatexDocument],
        bibliography_files: Iterable[str | Path],
        *,
        root: str | Path | None = None,
    ) -> CitationReport:
        citation_locations: dict[str, list[SourceLocation]] = defaultdict(list)
        for document in documents:
            if not isinstance(document, LatexDocument):
                raise TypeError("documents must contain only LatexDocument instances.")
            for citation in document.citations:
                citation_locations[citation.value].append(citation.location)

        definitions: dict[str, list[SourceLocation]] = defaultdict(list)
        missing_files: list[str] = []
        malformed_entries: list[SourceLocation] = []
        root_path = Path(root).resolve() if root is not None else None
        bibliography_paths = sorted(
            {Path(item) for item in bibliography_files},
            key=lambda item: item.as_posix(),
        )
        for bibliography_file in bibliography_paths:
            actual_path = bibliography_file
            if root_path is not None and not actual_path.is_absolute():
                actual_path = root_path / actual_path
            if root_path is not None:
                try:
                    actual_path.resolve().relative_to(root_path)
                except ValueError as error:
                    raise ValueError(
                        "Bibliography files must remain inside the workspace root."
                    ) from error
            display_path = self._display_path(actual_path, root_path)
            if not actual_path.is_file():
                missing_files.append(display_path)
                continue
            try:
                text = actual_path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError):
                missing_files.append(display_path)
                continue
            text = self._strip_comments(text)
            valid_starts: set[int] = set()
            for match in _BIB_ENTRY.finditer(text):
                valid_starts.add(match.start())
                key = match.group(1).strip()
                location = SourceLocation(
                    display_path,
                    text.count("\n", 0, match.start()) + 1,
                )
                if not self._entry_is_balanced(text, match.start()):
                    malformed_entries.append(location)
                    continue
                definitions[key].append(location)
            for start in _BIB_START.finditer(text):
                if start.group(1).lower() in _NON_ENTRY_TYPES or start.start() in valid_starts:
                    continue
                malformed_entries.append(
                    SourceLocation(
                        display_path,
                        text.count("\n", 0, start.start()) + 1,
                    )
                )

        missing = tuple(
            CitationIssue(key, tuple(citation_locations[key]))
            for key in sorted(citation_locations.keys() - definitions.keys())
        )
        unused = tuple(
            CitationIssue(key, tuple(definitions[key]))
            for key in sorted(definitions.keys() - citation_locations.keys())
        )
        duplicates = tuple(
            CitationIssue(key, tuple(definitions[key]))
            for key in sorted(definitions)
            if len(definitions[key]) > 1
        )
        return CitationReport(
            missing_bibliography_entries=missing,
            unused_bibliography_entries=unused,
            duplicate_citation_keys=duplicates,
            missing_bibliography_files=tuple(missing_files),
            malformed_bibliography_entries=tuple(malformed_entries),
        )

    @staticmethod
    def _strip_comments(text: str) -> str:
        lines: list[str] = []
        for line in text.splitlines(keepends=True):
            comment_at = None
            for index, character in enumerate(line):
                if character != "%":
                    continue
                backslashes = 0
                cursor = index - 1
                while cursor >= 0 and line[cursor] == "\\":
                    backslashes += 1
                    cursor -= 1
                if backslashes % 2 == 0:
                    comment_at = index
                    break
            if comment_at is None:
                lines.append(line)
            else:
                suffix = "\n" if line.endswith("\n") else ""
                lines.append(
                    line[:comment_at]
                    + (" " * (len(line) - comment_at - len(suffix)))
                    + suffix
                )
        return "".join(lines)

    @staticmethod
    def _entry_is_balanced(text: str, offset: int) -> bool:
        opener_at = next(
            (index for index in range(offset, len(text)) if text[index] in "{("),
            None,
        )
        if opener_at is None:
            return False
        opener = text[opener_at]
        closer = "}" if opener == "{" else ")"
        depth = 0
        for character in text[opener_at:]:
            if character == opener:
                depth += 1
            elif character == closer:
                depth -= 1
                if depth == 0:
                    return True
        return False

    @staticmethod
    def _display_path(path: Path, root: Path | None) -> str:
        if root is not None:
            try:
                return path.resolve().relative_to(root).as_posix()
            except ValueError:
                pass
        return path.as_posix()
