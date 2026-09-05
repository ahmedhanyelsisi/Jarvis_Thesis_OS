class ResearchIntelligenceError(Exception):
    """Base exception for Stone 20."""
    pass

class SanitizationError(ResearchIntelligenceError):
    """Raised when a paper fails security and sanitization checks."""
    pass

class PDFExtractionError(ResearchIntelligenceError):
    """Raised when PDF extraction fails or file is corrupted."""
    pass

class CitationGraphError(ResearchIntelligenceError):
    """Raised when citation graph operations fail."""
    pass

class IndexingError(ResearchIntelligenceError):
    """Raised when ChromaDB semantic indexing fails."""
    pass
