class AcademicMemoryError(Exception):
    """Base exception for Stone 22 Academic Memory Layer."""
    pass

class MemoryGovernanceError(AcademicMemoryError):
    """Raised when memory fails sanitization or boundary checks."""
    pass

class MemoryStorageError(AcademicMemoryError):
    """Raised during SQLite or JSON persistence failures."""
    pass
