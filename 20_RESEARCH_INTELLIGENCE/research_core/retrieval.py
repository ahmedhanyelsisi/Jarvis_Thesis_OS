from typing import List, Dict, Any
from .indexer import ResearchIndexer

class ResearchRetrieval:
    """Wraps indexer to provide formatted semantic search."""

    def __init__(self, indexer: ResearchIndexer):
        self._indexer = indexer

    def search_papers(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Searches the local research index."""
        hits = self._indexer.search(query, n_results=top_n)
        return hits
