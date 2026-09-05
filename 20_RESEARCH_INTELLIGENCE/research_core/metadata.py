import abc
from typing import Dict, List, Optional

class ResearchMetadataProvider(abc.ABC):
    
    @abc.abstractmethod
    def resolve_doi(self, doi: str) -> Optional[Dict[str, str]]:
        pass
        
    @abc.abstractmethod
    def get_citations(self, paper_id: str) -> List[str]:
        pass
        
    @abc.abstractmethod
    def get_metadata(self, paper_id: str) -> Optional[Dict[str, str]]:
        pass

class MockMetadataProvider(ResearchMetadataProvider):
    """Mock provider as instructed by architecture decisions."""
    
    def resolve_doi(self, doi: str) -> Optional[Dict[str, str]]:
        if not doi:
            return None
        return {"title": f"Resolved Mock Paper for {doi}", "author": "Mock Author", "year": "2024"}
        
    def get_citations(self, paper_id: str) -> List[str]:
        return [f"mock_ref_{i}" for i in range(3)]
        
    def get_metadata(self, paper_id: str) -> Optional[Dict[str, str]]:
        return {"title": "Mock Title", "author": "Mock Author"}
