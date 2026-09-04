import logging
import uuid
import chromadb
from pathlib import Path
from typing import List

from jarvis_core.interfaces import IEventBus
from thesis_session.file_access import SafeAgentFileAccess
from .exceptions import IndexError
from .models import ThesisChunk

logger = logging.getLogger(__name__)

class ThesisIndexer:
    """Listens to session events, reads files safely, and maintains a local ChromaDB index."""
    
    def __init__(self, event_bus: IEventBus, file_access: SafeAgentFileAccess, session_id: str):
        self._event_bus = event_bus
        self._file_access = file_access
        self._session_id = session_id
        
        # Use an ephemeral client for runtime memory embedding, scoped to this session
        self._chroma_client = chromadb.EphemeralClient()
        self._collection = self._chroma_client.get_or_create_collection(name=f"thesis_index_{session_id}")
        
        self._subscribe()

    def _subscribe(self) -> None:
        self._event_bus.subscribe("session.chapter.changed", self._on_chapter_changed)
        # Assuming we might want to listen to file written events in the future
        
    def _on_chapter_changed(self, payload: dict) -> None:
        if payload.get("session_id") != self._session_id:
            return
        
        chapter = payload.get("active_chapter")
        if chapter:
            # When active chapter changes, we ensure it's indexed
            file_path = f"{chapter}.tex"
            try:
                self.index_file(file_path)
            except Exception as e:
                logger.error(f"Failed to index chapter {chapter}: {e}")

    def index_file(self, file_path: str) -> None:
        """Read a file safely and chunk it into the index."""
        try:
            content = self._file_access.read_file(file_path)
        except Exception as e:
            raise IndexError(f"Failed to read {file_path} for indexing: {e}") from e
            
        chunks = self._chunk_text(file_path, content)
        self._store_chunks(chunks)

    def _chunk_text(self, file_path: str, text: str, chunk_size: int = 500) -> List[ThesisChunk]:
        """Simple chunking logic by lines/paragraphs for LaTeX."""
        chunks = []
        paragraphs = text.split("\n\n")
        current_chunk = []
        current_length = 0
        
        for p in paragraphs:
            if current_length + len(p) > chunk_size and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(ThesisChunk(
                    chunk_id=str(uuid.uuid4()),
                    file_path=file_path,
                    content=chunk_text,
                    metadata={"source": file_path}
                ))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(p)
            current_length += len(p)
            
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(ThesisChunk(
                chunk_id=str(uuid.uuid4()),
                file_path=file_path,
                content=chunk_text,
                metadata={"source": file_path}
            ))
            
        return chunks

    def _store_chunks(self, chunks: List[ThesisChunk]) -> None:
        if not chunks:
            return
            
        ids = [c.chunk_id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]
        
        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
        except Exception as e:
            raise IndexError(f"Failed to store chunks in vector DB: {e}") from e

    def search(self, query: str, n_results: int = 5) -> dict:
        """Query the local index."""
        try:
            return self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
        except Exception as e:
            return {"ids": [[]], "documents": [[]], "distances": [[]], "metadatas": [[]]}
