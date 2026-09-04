import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock
from dataclasses import FrozenInstanceError

from thesis_session.models import ThesisSession, ChapterState, ChapterStatus, SessionSnapshot
from thesis_session.manager import ThesisSessionManager
from thesis_session.file_access import SafeAgentFileAccess
from thesis_session.exceptions import PathViolationError, SessionError

# ---------------------------------------------------------------------------
# Models Immutability Tests
# ---------------------------------------------------------------------------

def test_models_are_immutable():
    c = ChapterState(chapter_name="intro", file_path="intro.tex")
    with pytest.raises(FrozenInstanceError):
        c.chapter_name = "hack"

    s = ThesisSession(session_id="123", thesis_root="/tmp")
    with pytest.raises(FrozenInstanceError):
        s.session_id = "456"

# ---------------------------------------------------------------------------
# SafeAgentFileAccess Tests
# ---------------------------------------------------------------------------

def test_file_access_allowed_paths(tmp_path):
    fa = SafeAgentFileAccess(thesis_root=tmp_path)
    
    # Write safe file
    fa.write_file("main.tex", "Hello")
    assert fa.read_file("main.tex") == "Hello"

def test_file_access_path_traversal_blocked(tmp_path):
    fa = SafeAgentFileAccess(thesis_root=tmp_path)
    
    with pytest.raises(PathViolationError, match="Path traversal blocked"):
        fa.read_file("../outside.tex")

def test_file_access_absolute_path_blocked(tmp_path):
    fa = SafeAgentFileAccess(thesis_root=tmp_path)
    
    abs_path = os.path.abspath("/etc/passwd")
    with pytest.raises(PathViolationError, match="Absolute paths forbidden"):
        fa.read_file(abs_path)

def test_file_access_null_byte_blocked(tmp_path):
    fa = SafeAgentFileAccess(thesis_root=tmp_path)
    
    with pytest.raises(PathViolationError, match="Null byte injection"):
        fa.read_file("main\x00.tex")

# ---------------------------------------------------------------------------
# ThesisSessionManager Tests
# ---------------------------------------------------------------------------

def test_session_manager_lifecycle(tmp_path):
    mock_bus = MagicMock()
    sm = ThesisSessionManager(event_bus=mock_bus, thesis_root=tmp_path)
    
    session = sm.get_session()
    assert session.thesis_root == str(tmp_path.resolve())
    
    # Set active chapter
    s2 = sm.set_active_chapter("chapter1")
    assert s2.active_chapter == "chapter1"
    assert len(s2.chapters) == 1
    assert s2.chapters[0].chapter_name == "chapter1"
    mock_bus.publish.assert_called_with("session.chapter.changed", {"session_id": session.session_id, "active_chapter": "chapter1"})
    
    # Record build
    s3 = sm.record_build("task-123")
    assert "task-123" in s3.build_task_ids
    
    # Check persistence
    jarvis_dir = tmp_path / ".jarvis"
    session_file = jarvis_dir / "session.json"
    assert session_file.exists()
    
    data = json.loads(session_file.read_text(encoding="utf-8"))
    assert data["session_id"] == session.session_id
    assert data["active_chapter"] == "chapter1"

def test_session_manager_persistence_restore(tmp_path):
    mock_bus = MagicMock()
    
    # Create initial
    sm1 = ThesisSessionManager(event_bus=mock_bus, thesis_root=tmp_path)
    sm1.set_active_chapter("intro")
    sid = sm1.get_session().session_id
    
    # Reload
    sm2 = ThesisSessionManager(event_bus=mock_bus, thesis_root=tmp_path)
    assert sm2.get_session().session_id == sid
    assert sm2.get_session().active_chapter == "intro"
    assert sm2.get_session().chapters[0].chapter_name == "intro"

def test_session_manager_event_bus_failure_swallowed(tmp_path):
    mock_bus = MagicMock()
    mock_bus.publish.side_effect = Exception("Bus down")
    
    sm = ThesisSessionManager(event_bus=mock_bus, thesis_root=tmp_path)
    # Should not raise exception
    sm.set_active_chapter("chapter2")

# ---------------------------------------------------------------------------
# Boundary / AST tests
# ---------------------------------------------------------------------------

def test_forbidden_imports_thesis_session():
    import ast
    session_dir = Path("08_THESIS_SESSION/thesis_session")
    forbidden = {"subprocess", "requests", "socket", "asyncio", "multiprocessing", "ServiceRegistry"}
    
    for py_file in session_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, f"Forbidden import {alias.name} in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module.split(".")[0] not in forbidden, f"Forbidden import {node.module} in {py_file}"
                    assert "ServiceRegistry" not in node.module
