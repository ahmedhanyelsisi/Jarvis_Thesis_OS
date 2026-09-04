from dataclasses import dataclass, field
from typing import Tuple, Optional
from pathlib import Path

@dataclass(frozen=True)
class BuildPolicy:
    """Controls strict execution policies for the LaTeX compilation sandbox."""
    timeout_seconds: int = 60
    shell_execution_permission: bool = False
    maximum_output_size: int = 10485760  # 10 MB limit for log files

@dataclass(frozen=True)
class BuildRequest:
    target_dir: Path
    main_file: str = "main.tex"
    policy: BuildPolicy = field(default_factory=BuildPolicy)

@dataclass(frozen=True)
class LatexDiagnostic:
    type: str  # "error" or "warning"
    line: Optional[int]
    message: str
    raw_context: str

@dataclass(frozen=True)
class CompilationArtifact:
    artifact_type: str  # "pdf", "log", "aux", etc.
    path: Path

@dataclass(frozen=True)
class BuildResult:
    success: bool
    duration_seconds: float
    diagnostics: Tuple[LatexDiagnostic, ...]
    artifacts: Tuple[CompilationArtifact, ...]
