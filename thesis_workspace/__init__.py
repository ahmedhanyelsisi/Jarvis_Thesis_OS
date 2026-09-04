"""Stone 10: Thesis Workspace & Document Intelligence Layer."""

from .citation_checker import CitationChecker
from .document_models import (
    ChangeAnalysis,
    CitationIssue,
    CitationReport,
    DocumentElement,
    FigureElement,
    LatexEnvironment,
    LatexDocument,
    ParseDiagnostic,
    ProposedModification,
    SourceLocation,
    ThesisStructure,
)
from .file_operations import SafeFileOperations, WorkspaceLockError
from .latex_parser import LatexParser, UnsupportedEncodingError
from .workspace_manager import ThesisWorkspaceManager, WorkspaceManager

__all__ = [
    "ChangeAnalysis",
    "CitationChecker",
    "CitationIssue",
    "CitationReport",
    "DocumentElement",
    "FigureElement",
    "LatexEnvironment",
    "LatexDocument",
    "LatexParser",
    "ParseDiagnostic",
    "ProposedModification",
    "SafeFileOperations",
    "SourceLocation",
    "ThesisStructure",
    "ThesisWorkspaceManager",
    "UnsupportedEncodingError",
    "WorkspaceManager",
    "WorkspaceLockError",
]
