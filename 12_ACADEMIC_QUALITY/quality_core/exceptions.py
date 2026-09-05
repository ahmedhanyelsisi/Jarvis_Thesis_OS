class QualityEvaluationError(Exception):
    """Base exception for Academic Quality layer."""
    pass

class QualityHistoryError(QualityEvaluationError):
    """Raised for persistence or history retrieval errors."""
    pass

class MetricValidationError(QualityEvaluationError):
    """Raised when an invalid score is assigned to a metric."""
    pass
