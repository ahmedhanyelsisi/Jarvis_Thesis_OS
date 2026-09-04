class LatexEngineError(Exception):
    """Base exception for LaTeX engine failures."""
    pass

class CompilationTimeoutError(LatexEngineError):
    """Raised when compilation exceeds the configured timeout."""
    pass

class WorkspaceNotFoundError(LatexEngineError):
    """Raised when the target workspace or main file cannot be located."""
    pass

class PolicyViolationError(LatexEngineError):
    """Raised when a strict build policy is violated."""
    pass
