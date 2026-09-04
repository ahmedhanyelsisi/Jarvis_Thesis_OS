class WorkflowError(Exception):
    """Base exception for the Academic Workflow Orchestrator."""
    pass

class WorkflowStateError(WorkflowError):
    """Raised when a workflow transitions to an invalid state."""
    pass

class CheckpointError(WorkflowError):
    """Raised when human approval logic fails or times out."""
    pass

class InfiniteLoopError(WorkflowError):
    """Raised when a workflow exceeds maximum node transitions."""
    pass

class WorkflowPersistenceError(WorkflowError):
    """Raised when persistence layer encounters a critical error or security violation."""
    pass
