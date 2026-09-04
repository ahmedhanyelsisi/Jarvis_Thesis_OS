"""Compatibility imports for the canonical vector store."""

from knowledge_system.database.vector_store import (
    Embedder,
    EmbeddingConfig,
    EmbeddingConfigurationError,
    LocalHashEmbedder,
    SentenceTransformerEmbedder,
    VectorStore,
)

__all__ = [
    "Embedder",
    "EmbeddingConfig",
    "EmbeddingConfigurationError",
    "LocalHashEmbedder",
    "SentenceTransformerEmbedder",
    "VectorStore",
]
