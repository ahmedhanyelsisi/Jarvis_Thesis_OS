"""
JARVIS THESIS OS - THESIS SESSION MANAGER (STONE 15)
Stateful tracking and secure agent file I/O layer.
"""

from .exceptions import SessionError, SessionNotFoundError, PathViolationError, SessionPersistenceError
from .models import ThesisSession, ChapterState, ChapterStatus, SessionSnapshot
from .file_access import SafeAgentFileAccess
from .manager import ThesisSessionManager
from .activator import SystemActivator

__all__ = [
    "SessionError",
    "SessionNotFoundError", 
    "PathViolationError",
    "SessionPersistenceError",
    "ThesisSession",
    "ChapterState",
    "ChapterStatus",
    "SessionSnapshot",
    "SafeAgentFileAccess",
    "ThesisSessionManager",
    "SystemActivator"
]
