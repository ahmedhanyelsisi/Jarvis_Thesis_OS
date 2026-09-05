class PipelineError(Exception):
    """Base exception for Stone 23 Thesis Pipeline Layer."""
    pass

class ApprovalError(PipelineError):
    """Raised when an invalid or fake approval is detected."""
    pass

class StateTransitionError(PipelineError):
    """Raised when an illegal pipeline state transition is attempted."""
    pass

class RevisionLimitError(PipelineError):
    """Raised when a chapter exceeds the maximum allowed revision loops."""
    pass

class ChapterDependencyError(PipelineError):
    """Raised when chapter sequences or dependencies are corrupted."""
    pass
