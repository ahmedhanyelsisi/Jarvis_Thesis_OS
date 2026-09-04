class SessionError(Exception):
    """Base exception for the Thesis Session layer."""
    pass

class SessionNotFoundError(SessionError):
    """Raised when a session cannot be found or loaded."""
    pass

class PathViolationError(SessionError):
    """Raised when an agent attempts an unsafe file path access."""
    pass

class SessionPersistenceError(SessionError):
    """Raised when disk read/write of session snapshot fails."""
    pass
