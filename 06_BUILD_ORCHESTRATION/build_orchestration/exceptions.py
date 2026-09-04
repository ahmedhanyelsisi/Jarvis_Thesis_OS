class BuildOrchestrationError(Exception):
    """Base exception for Build Orchestration."""
    pass

class InvalidStateTransitionError(BuildOrchestrationError):
    """Raised when an invalid task state transition is attempted."""
    pass
