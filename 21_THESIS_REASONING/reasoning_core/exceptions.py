class ReasoningError(Exception):
    """Base exception for Stone 21 Thesis Reasoning Layer."""
    pass

class EvidenceError(ReasoningError):
    """Raised when evidence mapping fails or is invalid."""
    pass

class ContradictionError(ReasoningError):
    """Raised during contradiction detection anomalies."""
    pass
