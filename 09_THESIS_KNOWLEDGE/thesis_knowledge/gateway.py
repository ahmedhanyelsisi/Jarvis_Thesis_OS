from typing import List, Any
from .models import SemanticResult, ASTNode, ContextPackage
from .indexer import ThesisIndexer
from .context_builder import ContextBuilder
from .copilot_bridge import CopilotBridge
from .exceptions import RetrievalError

class ContextGateway:
    """Public interface exposed to AgentContext."""
    
    def __init__(self, indexer: ThesisIndexer, bridge: CopilotBridge, builder: ContextBuilder):
        self._indexer = indexer
        self._bridge = bridge
        self._builder = builder

    def search_thesis(self, query: str) -> List[SemanticResult]:
        """Search the semantic index for relevant chunks."""
        if not isinstance(query, str) or not query.strip():
            return []
            
        raw_results = self._indexer.search(query, n_results=5)
        
        results = []
        if raw_results and raw_results.get("ids") and raw_results["ids"][0]:
            ids = raw_results["ids"][0]
            docs = raw_results["documents"][0]
            metadatas = raw_results["metadatas"][0]
            distances = raw_results["distances"][0] if "distances" in raw_results else [0.0]*len(ids)
            
            for i in range(len(ids)):
                results.append(SemanticResult(
                    chunk_id=ids[i],
                    file_path=metadatas[i].get("source", ""),
                    content=docs[i],
                    distance=float(distances[i])
                ))
        return results

    def get_document_structure(self, target: str) -> ASTNode:
        """Fetch structural AST representation of the thesis."""
        return self._bridge.get_structure(target)
        
    def retrieve_citations(self, reference: str) -> List[str]:
        """Fetch citations used. For now, simple mock lookup."""
        # Future enhancement: proper .bib parsing, but we fulfill the contract here
        ctx = self._bridge._copilot.thesis_context()
        return [r for r in ctx.references if reference.lower() in r.lower()]

    def build_context(self, goal: str) -> ContextPackage:
        """Build an academic context package for the given goal."""
        results = self.search_thesis(goal)
        structure = self.get_document_structure("thesis")
        return self._builder.build_context(goal, results, [structure])
