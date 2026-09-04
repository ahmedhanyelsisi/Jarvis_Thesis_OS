class AgentError(Exception):
    """Base exception for Academic Agents."""
    pass

class TaskExecutionError(AgentError):
    """Raised when a task fails execution."""
    pass

class PolicyViolationError(AgentError):
    """Raised when an agent violates the AgentExecutionPolicy."""
    pass
