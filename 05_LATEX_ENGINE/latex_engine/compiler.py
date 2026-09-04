import subprocess
import time
from pathlib import Path
from typing import Tuple

from .models import BuildRequest, BuildResult, LatexDiagnostic
from .workspace import WorkspaceManager
from .log_parser import LogParser
from .artifacts import ArtifactDiscoverer
from .exceptions import CompilationTimeoutError, LatexEngineError, PolicyViolationError

class LatexCompiler:
    """Executes pdflatex safely via strictly constrained subprocesses."""
    
    def compile(self, request: BuildRequest) -> BuildResult:
        start_time = time.time()
        
        # Validate workspace strictly
        root = WorkspaceManager.validate_workspace(request)
        
        # Enforce BuildPolicy
        if request.policy.shell_execution_permission:
            raise PolicyViolationError("shell_execution_permission=True is strictly forbidden in this subsystem.")
            
        command = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            request.main_file
        ]
        
        try:
            process = subprocess.run(
                command,
                cwd=str(root),
                shell=False,  # strictly enforce False
                capture_output=True,
                timeout=request.policy.timeout_seconds
            )
        except subprocess.TimeoutExpired as e:
            raise CompilationTimeoutError(f"Compilation exceeded policy limit of {request.policy.timeout_seconds}s") from e
        except Exception as e:
            raise LatexEngineError(f"Subprocess failure: {str(e)}") from e

        success = (process.returncode == 0)
        
        # Gather diagnostics
        diagnostics = []
        log_file = root / (Path(request.main_file).stem + ".log")
        if log_file.exists():
            size = log_file.stat().st_size
            if size <= request.policy.maximum_output_size:
                content = log_file.read_text(encoding="utf-8", errors="replace")
                diagnostics = LogParser.parse(content)
            else:
                diagnostics.append(LatexDiagnostic(
                    type="warning",
                    line=None,
                    message=f"Log file exceeded maximum size ({size} > {request.policy.maximum_output_size}). Output truncated.",
                    raw_context=""
                ))
                
        # Discover artifacts
        artifacts = ArtifactDiscoverer.collect(root, request.main_file)
        
        duration = time.time() - start_time
        return BuildResult(
            success=success,
            duration_seconds=duration,
            diagnostics=tuple(diagnostics),
            artifacts=artifacts
        )
