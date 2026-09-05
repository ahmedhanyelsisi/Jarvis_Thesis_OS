import json
import networkx as nx
from pathlib import Path
from typing import List, Dict

from .models import CitationNode
from .exceptions import CitationGraphError

class CitationGraphManager:
    """Manages the network of citations locally using NetworkX."""

    def __init__(self, workspace_root: str, session_id: str):
        self._base_path = Path(workspace_root) / ".jarvis" / "research_index"
        
        # Path traversal mitigation
        clean_session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if clean_session_id != session_id:
            raise CitationGraphError("Invalid session_id format.")
            
        self._graph_path = self._base_path / f"citation_graph_{clean_session_id}.json"
        
        if not self._graph_path.resolve().is_relative_to(self._base_path.resolve()):
            raise CitationGraphError("Path traversal blocked.")
            
        self._graph_path.parent.mkdir(parents=True, exist_ok=True)
        self._graph = nx.DiGraph()
        self._load()

    def _load(self):
        if self._graph_path.exists():
            try:
                with self._graph_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self._graph = nx.node_link_graph(data)
            except Exception as e:
                raise CitationGraphError(f"Failed to load citation graph: {e}")

    def _save(self):
        try:
            data = nx.node_link_data(self._graph)
            temp_path = self._graph_path.with_suffix(".json.tmp")
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self._graph_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise CitationGraphError(f"Failed to save citation graph: {e}")

    def add_paper(self, paper_id: str, references: List[str]):
        """Adds a paper and its references (outgoing edges)."""
        if not self._graph.has_node(paper_id):
            self._graph.add_node(paper_id)
            
        for ref in references:
            if not self._graph.has_node(ref):
                self._graph.add_node(ref)
            self._graph.add_edge(paper_id, ref)
            
        self._save()

    def get_influential_papers(self, top_n: int = 5) -> List[str]:
        """Calculates PageRank to find most influential papers."""
        if len(self._graph) == 0:
            return []
        try:
            pr = nx.pagerank(self._graph)
            sorted_nodes = sorted(pr.items(), key=lambda x: x[1], reverse=True)
            return [node for node, score in sorted_nodes[:top_n]]
        except Exception as e:
            raise CitationGraphError(f"Failed to calculate influence: {e}")

    def get_node(self, paper_id: str) -> CitationNode:
        if not self._graph.has_node(paper_id):
            raise CitationGraphError(f"Paper {paper_id} not in graph.")
            
        # cited_papers = incoming edges (papers that cite this one)
        # references = outgoing edges (papers this one cites)
        cited_by = tuple(self._graph.predecessors(paper_id))
        refs = tuple(self._graph.successors(paper_id))
        
        return CitationNode(
            paper_id=paper_id,
            cited_papers=cited_by,
            references=refs
        )
