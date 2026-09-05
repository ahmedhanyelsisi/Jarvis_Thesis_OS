from typing import List, Dict, Any, Union
from pathlib import Path

from .models import ResearchPaper, ResearchGap
from .pdf_engine import PDFEngine
from .parser import PaperParser
from .indexer import ResearchIndexer
from .retrieval import ResearchRetrieval
from .gap_detector import GapDetector

class ResearchGateway:
    """Safe interface exposed to AgentContext. Protects direct file/LLM access."""
    
    def __init__(self, workspace_root: str, session_id: str):
        self._pdf_engine = PDFEngine()
        self._indexer = ResearchIndexer(workspace_root, session_id)
        self._retrieval = ResearchRetrieval(self._indexer)
        # Note: Citation graph and metadata provider can be wired here

    def ingest_paper(self, file_path: Union[str, Path]) -> ResearchPaper:
        """Ingests a PDF, parses it securely, and adds to index."""
        raw_data = self._pdf_engine.extract_paper(file_path)
        paper = PaperParser.parse(raw_data)
        self._indexer.index_paper(paper)
        return paper

    def search_research(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Returns semantic matches from ingested literature."""
        return self._retrieval.search_papers(query, top_n)

    def find_research_gaps(self, papers: List[ResearchPaper]) -> List[ResearchGap]:
        return GapDetector.analyze_gaps(papers)
        
    def get_paper_context(self, paper_id: str) -> str:
        # Simplistic stub for retrieving a specific paper by ID for agents
        hits = self._indexer.search(paper_id, n_results=1)
        if hits:
            return hits[0].get("document", "")
        return ""

    def compare_methodologies(self) -> str:
        # Stub for extracting methodology profiles
        return "Methodology comparison not fully implemented in mock layer."
