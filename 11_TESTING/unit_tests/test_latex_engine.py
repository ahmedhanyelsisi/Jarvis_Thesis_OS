import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from latex_engine import (
    BuildPolicy,
    BuildRequest,
    BuildResult,
    LatexCompiler,
    LatexDiagnostic,
    WorkspaceManager,
    LogParser,
    ArtifactDiscoverer,
    WorkspaceNotFoundError,
    CompilationTimeoutError,
    PolicyViolationError
)

def test_immutable_models():
    policy = BuildPolicy(timeout_seconds=30)
    assert policy.timeout_seconds == 30
    assert policy.shell_execution_permission is False
    
    # Frozen models should raise on modification
    with pytest.raises(Exception): # Dataclass FrozenInstanceError
        policy.timeout_seconds = 100

def test_workspace_discovery_valid(tmp_path):
    # Setup mock workspace
    main_tex = tmp_path / "main.tex"
    main_tex.write_text("Hello World")
    
    req = BuildRequest(target_dir=tmp_path, main_file="main.tex")
    root = WorkspaceManager.validate_workspace(req)
    assert root == tmp_path.resolve()

def test_workspace_discovery_invalid_dir(tmp_path):
    invalid_dir = tmp_path / "does_not_exist"
    req = BuildRequest(target_dir=invalid_dir)
    with pytest.raises(WorkspaceNotFoundError):
        WorkspaceManager.validate_workspace(req)

def test_workspace_discovery_missing_main(tmp_path):
    req = BuildRequest(target_dir=tmp_path, main_file="missing.tex")
    with pytest.raises(WorkspaceNotFoundError, match="missing.tex not found"):
        WorkspaceManager.validate_workspace(req)

def test_log_parser_errors():
    mock_log = (
        "This is a log.\n"
        "! Undefined control sequence.\n"
        "l.42 \\fakecommand\n"
        "Some other text.\n"
    )
    diagnostics = LogParser.parse(mock_log)
    assert len(diagnostics) == 1
    assert diagnostics[0].type == "error"
    assert diagnostics[0].line == 42
    assert "Undefined control sequence" in diagnostics[0].message

def test_log_parser_warnings():
    mock_log = (
        "LaTeX Warning: Citation `foo' on page 1 undefined on input line 10.\n"
        "Package hyperref Warning: Suppressing link on input line 12.\n"
    )
    diagnostics = LogParser.parse(mock_log)
    assert len(diagnostics) == 2
    assert diagnostics[0].type == "warning"
    assert diagnostics[0].line == 10
    assert "Citation `foo' on page 1 undefined" in diagnostics[0].message
    assert diagnostics[1].type == "warning"
    assert diagnostics[1].line == 12
    assert "Suppressing link" in diagnostics[1].message

def test_log_parser_layout_warnings():
    mock_log = (
        r"Overfull \hbox (10.0pt too wide) in paragraph at lines 4--6" + "\n"
        r"Underfull \vbox (badness 10000) has occurred while \output is active" + "\n"
        r"Overfull \hbox (15.0pt too wide) detected at line 12" + "\n"
    )
    diagnostics = LogParser.parse(mock_log)
    assert len(diagnostics) == 3
    
    assert diagnostics[0].type == "warning"
    assert diagnostics[0].line == 4
    assert r"Overfull \hbox" in diagnostics[0].message
    
    assert diagnostics[1].type == "warning"
    assert diagnostics[1].line is None
    assert r"Underfull \vbox" in diagnostics[1].message
    
    assert diagnostics[2].type == "warning"
    assert diagnostics[2].line == 12
    assert r"Overfull \hbox" in diagnostics[2].message

@patch("subprocess.run")
def test_compiler_success(mock_run, tmp_path):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text("dummy")
    
    # Create fake artifacts
    (tmp_path / "main.log").write_text("LaTeX Warning: test on input line 5.")
    (tmp_path / "main.pdf").touch()
    
    mock_run.return_value = MagicMock(returncode=0)
    
    compiler = LatexCompiler()
    req = BuildRequest(target_dir=tmp_path)
    result = compiler.compile(req)
    
    assert result.success is True
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].line == 5
    
    artifact_types = [a.artifact_type for a in result.artifacts]
    assert "pdf" in artifact_types
    assert "log" in artifact_types

@patch("subprocess.run")
def test_compiler_timeout(mock_run, tmp_path):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text("dummy")
    
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="pdflatex", timeout=60)
    
    compiler = LatexCompiler()
    req = BuildRequest(target_dir=tmp_path)
    with pytest.raises(CompilationTimeoutError):
        compiler.compile(req)

def test_compiler_enforces_shell_policy(tmp_path):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text("dummy")
    
    policy = BuildPolicy(shell_execution_permission=True)
    req = BuildRequest(target_dir=tmp_path, policy=policy)
    
    compiler = LatexCompiler()
    with pytest.raises(PolicyViolationError, match="strictly forbidden"):
        compiler.compile(req)

def test_forbidden_imports():
    """Verify that latex_engine strictly respects boundaries."""
    engine_dir = Path("05_LATEX_ENGINE/latex_engine")
    import ast
    
    forbidden = {"socket", "requests", "urllib", "aiohttp", "httpx"}
    
    for py_file in engine_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, f"Forbidden import {alias.name} in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module.split(".")[0] not in forbidden, f"Forbidden import {node.module} in {py_file}"
