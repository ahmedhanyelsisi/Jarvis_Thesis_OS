"""Persistent database adapters used by the knowledge system."""

from .metadata_store import MetadataStore
from .vector_store import (
    Embedder,
    EmbeddingConfig,
    EmbeddingConfigurationError,
    LocalHashEmbedder,
    SentenceTransformerEmbedder,
    VectorStore,
)

__all__ = [
    "EmbeddingConfig",
    "EmbeddingConfigurationError",
    "Embedder",
    "LocalHashEmbedder",
    "MetadataStore",
    "SentenceTransformerEmbedder",
    "VectorStore",
]
