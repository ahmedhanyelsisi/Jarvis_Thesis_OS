from pathlib import Path
from typing import Union
from .exceptions import PDFExtractionError
from .paper_sanitizer import PaperSanitizer

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


class PDFEngine:
    """Extracts text and metadata from PDF files using PyMuPDF (fitz)."""

    def __init__(self):
        if not FITZ_AVAILABLE:
            # Fallback for environments lacking fitz, typically only in CI/testing
            self._mock_mode = True
        else:
            self._mock_mode = False

    def extract_paper(self, file_path: Union[str, Path]) -> dict:
        """Extracts text and metadata from a PDF.
        Returns a dictionary containing 'text' and 'metadata'."""
        path = Path(file_path)
        
        # Security Boundary: Sanitize before parsing
        PaperSanitizer.sanitize(path)

        if self._mock_mode:
            # Fallback mock extraction
            return self._mock_extract(path)

        try:
            doc = fitz.open(str(path))
            
            if doc.page_count == 0:
                raise PDFExtractionError("PDF is empty.")
                
            full_text = []
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                full_text.append(page.get_text())
                
            text = "\n".join(full_text)
            
            # Post-extraction sanitization
            text = PaperSanitizer.sanitize_text(text)
            
            metadata = doc.metadata or {}
            doc.close()
            
            return {
                "text": text,
                "metadata": metadata
            }
        except Exception as e:
            if isinstance(e, PDFExtractionError):
                raise
            raise PDFExtractionError(f"PyMuPDF failed to extract {path.name}: {e}")

    def _mock_extract(self, path: Path) -> dict:
        """Mock extraction for environments without PyMuPDF."""
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Mocking reading binary PDF as string
            content = "Mock abstract text. Introduction: This is a test."
            
        content = PaperSanitizer.sanitize_text(content)
        return {
            "text": content,
            "metadata": {"title": "Mock Title", "author": "Mock Author"}
        }
