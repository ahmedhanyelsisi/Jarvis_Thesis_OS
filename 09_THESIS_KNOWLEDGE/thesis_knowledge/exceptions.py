class ContextError(Exception):
    """Base exception for the Thesis Knowledge Layer."""
    pass

class RetrievalError(ContextError):
    """Raised when semantic search fails."""
    pass

class IndexError(ContextError):
    """Raised when indexing thesis documents fails."""
    pass
