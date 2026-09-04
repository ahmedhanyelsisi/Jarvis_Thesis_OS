from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional

@dataclass(frozen=True)
class ThesisChunk:
    """An immutable chunk of thesis text."""
    chunk_id: str
    file_path: str
    content: str
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class SemanticResult:
    """An immutable result from semantic retrieval."""
    chunk_id: str
    file_path: str
    content: str
    distance: float
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class ASTNode:
    """An immutable AST node representing thesis structure."""
    node_type: str  # e.g., "chapter", "section", "figure", "citation"
    title: str
    content: Optional[str]
    children: Tuple["ASTNode", ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ContextPackage:
    """An immutable, sanitized package of context for agents."""
    goal: str
    structured_ast: Tuple[ASTNode, ...]
    semantic_results: Tuple[SemanticResult, ...]
    sanitized_text: str
