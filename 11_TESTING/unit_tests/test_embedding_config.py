import json
from pathlib import Path

import pytest

from knowledge_system.database import (
    EmbeddingConfigurationError,
    LocalHashEmbedder,
    VectorStore,
)


def test_embedding_configuration_is_persisted_and_validated(tmp_path: Path):
    vector_path = tmp_path / "chroma"
    store = VectorStore(vector_path, embedder=LocalHashEmbedder(384))
    store.add_document("Persistent research knowledge")

    config_path = tmp_path / "embedding_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config == {
        "dimension": 384,
        "model": "blake2b-token-bigram",
        "model_version": "1",
        "provider": "local-hash",
    }

    reopened = VectorStore(vector_path, embedder=LocalHashEmbedder(384))
    assert reopened.search("research")

    with pytest.raises(EmbeddingConfigurationError, match="mismatch"):
        VectorStore(vector_path, embedder=LocalHashEmbedder(128))


def test_nonempty_legacy_collection_without_config_is_rejected(tmp_path: Path):
    vector_path = tmp_path / "chroma"
    store = VectorStore(vector_path)
    store.add_document("Existing vector")
    (tmp_path / "embedding_config.json").unlink()

    with pytest.raises(EmbeddingConfigurationError, match="non-empty collection"):
        VectorStore(vector_path)
