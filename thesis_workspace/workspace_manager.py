"""Kernel-facing facade for Stone 10 thesis workspace intelligence."""

from __future__ import annotations

import os
from pathlib import Path

from .citation_checker import CitationChecker
from .document_models import CitationReport, LatexDocument, ThesisStructure
from .file_operations import SafeFileOperations
from .latex_parser import LatexParser


class ThesisWorkspaceManager:
    """Discover, parse, validate, and safely modify one thesis workspace."""

    FIGURE_EXTENSIONS = frozenset({".eps", ".jpeg", ".jpg", ".pdf", ".png", ".svg", ".tif", ".tiff"})
    FIGURE_DIRECTORIES = frozenset(
        {"assets", "fig", "figs", "figure", "figures", "graphics", "image", "images"}
    )
    EXCLUDED_DIRECTORIES = frozenset({".git", ".pytest_cache", "__pycache__"})

    def __init__(
        self,
        root: str | Path,
        *,
        parser: LatexParser | None = None,
        citation_checker: CitationChecker | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"Thesis workspace does not exist: {self.root}")
        self.parser = parser or LatexParser()
        self.citation_checker = citation_checker or CitationChecker()
        self.file_operations = SafeFileOperations(self.root)

    def discover(self) -> ThesisStructure:
        files: list[Path] = []
        for current, directories, filenames in os.walk(self.root):
            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in self.EXCLUDED_DIRECTORIES and not directory.startswith(".")
            )
            for filename in sorted(filenames):
                candidate = Path(current) / filename
                try:
                    candidate.resolve().relative_to(self.root)
                except ValueError:
                    continue
                files.append(candidate)
        files.sort(key=lambda path: path.relative_to(self.root).as_posix())
        tex_paths = tuple(path for path in files if path.suffix.lower() == ".tex")
        bibliography_paths = tuple(path for path in files if path.suffix.lower() == ".bib")

        relative = lambda path: path.relative_to(self.root).as_posix()
        documents = tuple(
            self.parser.parse_file(path, display_path=relative(path)) for path in tex_paths
        )
        referenced_pdfs = self._referenced_pdf_paths(documents)
        figure_paths = tuple(
            path
            for path in files
            if path.suffix.lower() in self.FIGURE_EXTENSIONS
            and (
                path.suffix.lower() != ".pdf"
                or self._in_figure_directory(path)
                or path.resolve() in referenced_pdfs
            )
        )
        return ThesisStructure(
            root=self.root,
            tex_files=tuple(relative(path) for path in tex_paths),
            bibliography_files=tuple(relative(path) for path in bibliography_paths),
            figure_files=tuple(relative(path) for path in figure_paths),
            documents=documents,
        )

    scan = discover

    def check_citations(self, structure: ThesisStructure | None = None) -> CitationReport:
        snapshot = structure or self.discover()
        if snapshot.root != self.root:
            raise ValueError("Citation checks must use this manager's workspace root.")
        return self.citation_checker.check(
            snapshot.documents,
            snapshot.bibliography_files,
            root=snapshot.root,
        )

    def _referenced_pdf_paths(
        self,
        documents: tuple[LatexDocument, ...],
    ) -> frozenset[Path]:
        referenced: set[Path] = set()
        for document in documents:
            document_directory = (self.root / document.path).parent
            for figure in document.figures:
                if not figure.path:
                    continue
                reference = Path(figure.path)
                bases = (self.root / reference, document_directory / reference)
                for base in bases:
                    candidates = (base,) if base.suffix else (base.with_suffix(".pdf"),)
                    for candidate in candidates:
                        try:
                            resolved = candidate.resolve()
                            resolved.relative_to(self.root)
                        except ValueError:
                            continue
                        if resolved.suffix.lower() == ".pdf":
                            referenced.add(resolved)
        return frozenset(referenced)

    def _in_figure_directory(self, path: Path) -> bool:
        directories = path.relative_to(self.root).parts[:-1]
        return any(directory.lower() in self.FIGURE_DIRECTORIES for directory in directories)

WorkspaceManager = ThesisWorkspaceManager
