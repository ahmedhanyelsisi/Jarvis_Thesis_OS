import os
from pathlib import Path
from typing import List, Dict, Any

from .models import ResearchPaper
from .exceptions import IndexingError

class ResearchIndexer:
    """Semantic indexing using ChromaDB, strictly isolated per session."""

    def __init__(self, workspace_root: str, session_id: str):
        try:
            import chromadb
            from chromadb.config import Settings
            # Set up local chromadb in a specialized research namespace
            self._db_path = Path(workspace_root) / ".jarvis" / "research_index"
            self._db_path.mkdir(parents=True, exist_ok=True)
            
            self._client = chromadb.PersistentClient(
                path=str(self._db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            # Isolate collection by session to prevent cross-session leakage
            self._collection_name = f"research_{session_id}"
            self._collection = self._client.get_or_create_collection(self._collection_name)
            self._mock_mode = False
        except ImportError:
            # Fallback for environments lacking chromadb
            self._mock_mode = True
            self._mock_store = {}

    def index_paper(self, paper: ResearchPaper) -> None:
        if self._mock_mode:
            self._mock_store[paper.paper_id] = paper
            return

        try:
            # We index sections independently for better RAG
            ids = []
            documents = []
            metadatas = []
            
            for section_name, content in paper.sections.items():
                if len(content) < 50:
                    continue
                ids.append(f"{paper.paper_id}_{section_name}")
                documents.append(content)
                metadatas.append({
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "section": section_name
                })
                
            if documents:
                self._collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
        except Exception as e:
            raise IndexingError(f"Failed to index paper {paper.paper_id}: {e}")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        if self._mock_mode:
            return [{"id": k, "document": v.abstract, "metadata": {"paper_id": k}} for k, v in self._mock_store.items()][:n_results]

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            hits = []
            if results["documents"] and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    hits.append({
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i]
                    })
            return hits
        except Exception as e:
            raise IndexingError(f"Failed to search research index: {e}")
