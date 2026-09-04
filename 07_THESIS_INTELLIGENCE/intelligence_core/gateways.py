from typing import Any, Dict, List, Optional
from pathlib import Path

from .exceptions import LLMGatewayError, MemoryGatewayError

class LLMGateway:
    """
    Controlled gateway to LLM providers.
    Agents never call LLM providers directly. All calls route through here.
    Failures are trapped and surfaced as LLMGatewayError, never crashing the OS.
    """
    
    def __init__(self, provider=None):
        """
        provider: optional LLM backend. If None, operates in stub mode
                  (returns a predictable response) so all other subsystems remain testable.
        """
        self._provider = provider
        
    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Send a prompt to the LLM and return the response string."""
        if self._provider is None:
            # Stub mode: returns a safe, predictable value for testing
            return f"[LLM_STUB] Received prompt of length {len(prompt)}"
        try:
            result = self._provider.complete(prompt, context or {})
            # Contract: always return str. Guard against malformed provider responses.
            return result if isinstance(result, str) else ""
        except Exception as e:
            raise LLMGatewayError(f"LLM provider failed: {str(e)}") from e


class MemoryGateway:
    """
    Controlled gateway to knowledge/memory storage.
    Agents never query vector stores or SQLite directly. All access routes here.
    """
    
    def __init__(self, knowledge_manager=None):
        self._km = knowledge_manager
        
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the knowledge store and return structured results."""
        if self._km is None:
            return []
        try:
            results = self._km.search(query, top_k=top_k)
            # Normalize results into a consistent dict format
            return [
                r if isinstance(r, dict) else {"content": str(r), "score": None}
                for r in results
            ]
        except Exception as e:
            raise MemoryGatewayError(f"Memory search failed: {str(e)}") from e
            
    def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a document or chunk into the knowledge store."""
        if self._km is None:
            return
        try:
            self._km.store(content, metadata=metadata or {})
        except Exception as e:
            raise MemoryGatewayError(f"Memory store failed: {str(e)}") from e
