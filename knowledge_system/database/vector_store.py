"""Local Chroma vector storage with persistent embedding configuration."""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from dataclasses import asdict, dataclass
from importlib import metadata as package_metadata
from pathlib import Path
from typing import Any, Protocol, Sequence

import chromadb
from chromadb.config import Settings


_TOKEN_PATTERN = re.compile(r"\b\w+\b", flags=re.UNICODE)
_JSON_FIELDS_KEY = "_jarvis_json_fields"


class EmbeddingConfigurationError(RuntimeError):
    """Raised before use when stored and requested embeddings are incompatible."""


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    model_version: str
    dimension: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EmbeddingConfig":
        try:
            config = cls(
                provider=str(value["provider"]),
                model=str(value["model"]),
                model_version=str(value["model_version"]),
                dimension=int(value["dimension"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise EmbeddingConfigurationError(
                "embedding_config.json is missing required fields."
            ) from error
        if config.dimension < 1:
            raise EmbeddingConfigurationError("Embedding dimension must be positive.")
        return config


class Embedder(Protocol):
    @property
    def embedding_config(self) -> EmbeddingConfig:
        """Describe vectors produced by this embedder."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Convert text values to equal-length numeric vectors."""


class LocalHashEmbedder:
    """Deterministic lexical embeddings for fully offline operation."""

    def __init__(self, dimensions: int = 384) -> None:
        if dimensions < 32:
            raise ValueError("Embedding dimensions must be at least 32.")
        self.dimensions = dimensions

    @property
    def embedding_config(self) -> EmbeddingConfig:
        return EmbeddingConfig(
            provider="local-hash",
            model="blake2b-token-bigram",
            model_version="1",
            dimension=self.dimensions,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        tokens = _TOKEN_PATTERN.findall(text.casefold())
        features = tokens + [
            f"{left}::{right}" for left, right in zip(tokens, tokens[1:])
        ]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector


class SentenceTransformerEmbedder:
    """Opt-in embeddings from a local Sentence Transformers model."""

    def __init__(
        self,
        model_name_or_path: str,
        *,
        model_version: str | None = None,
        local_files_only: bool = True,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name_or_path = model_name_or_path
        self.model_version = model_version or package_metadata.version(
            "sentence-transformers"
        )
        self.model = SentenceTransformer(
            model_name_or_path,
            local_files_only=local_files_only,
        )
        dimension = self.model.get_sentence_embedding_dimension()
        if dimension is None:
            raise EmbeddingConfigurationError(
                "Sentence Transformer did not report an embedding dimension."
            )
        self.dimensions = int(dimension)

    @property
    def embedding_config(self) -> EmbeddingConfig:
        return EmbeddingConfig(
            provider="sentence-transformers",
            model=self.model_name_or_path,
            model_version=self.model_version,
            dimension=self.dimensions,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()


def _prepare_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    prepared: dict[str, Any] = {}
    json_fields: list[str] = []
    for key, value in (metadata or {}).items():
        name = str(key)
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            prepared[name] = value
        else:
            prepared[name] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            json_fields.append(name)
    if json_fields:
        prepared[_JSON_FIELDS_KEY] = json.dumps(json_fields)
    return prepared


def _restore_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    restored = dict(metadata or {})
    encoded_fields = restored.pop(_JSON_FIELDS_KEY, "[]")
    try:
        json_fields = json.loads(encoded_fields)
    except (TypeError, json.JSONDecodeError):
        json_fields = []
    for key in json_fields:
        if key in restored and isinstance(restored[key], str):
            try:
                restored[key] = json.loads(restored[key])
            except json.JSONDecodeError:
                pass
    return restored


class VectorStore:
    """Store and retrieve chunks in a local Chroma collection."""

    def __init__(
        self,
        persist_directory: str | Path | None = None,
        collection_name: str = "jarvis_knowledge",
        *,
        embedder: Embedder | None = None,
        embedding_config_path: str | Path | None = None,
    ) -> None:
        default_directory = (
            Path(__file__).resolve().parents[2]
            / "04_KNOWLEDGE_SYSTEM"
            / "data"
            / "chroma"
        )
        self.persist_directory = Path(
            persist_directory or default_directory
        ).expanduser().resolve()
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.embedding_config_path = Path(
            embedding_config_path
            or self.persist_directory.parent / "embedding_config.json"
        ).expanduser().resolve()
        self.embedder = embedder or LocalHashEmbedder()
        self.embedding_config = self.embedder.embedding_config
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.create_collection(collection_name)
        self._load_save_and_validate_embedding_config()

    def _load_save_and_validate_embedding_config(self) -> None:
        if self.embedding_config_path.exists():
            try:
                stored_value = json.loads(
                    self.embedding_config_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as error:
                raise EmbeddingConfigurationError(
                    f"Cannot read embedding configuration: {self.embedding_config_path}"
                ) from error
            stored_config = EmbeddingConfig.from_dict(stored_value)
            if stored_config != self.embedding_config:
                raise EmbeddingConfigurationError(
                    "Embedding configuration mismatch. "
                    f"Stored={stored_config.to_dict()}, "
                    f"requested={self.embedding_config.to_dict()}."
                )
            return

        if self.collection.count() > 0:
            raise EmbeddingConfigurationError(
                "A non-empty collection has no embedding_config.json; reindex it "
                "before opening to prevent a silent model mismatch."
            )
        self.embedding_config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.embedding_config_path.with_name(
            f"{self.embedding_config_path.name}.tmp"
        )
        temporary_path.write_text(
            json.dumps(self.embedding_config.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.embedding_config_path)

    def create_collection(self, name: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Collection name cannot be empty.")
        self.collection_name = name.strip()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self.collection

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings = self.embedder.embed(texts)
        if len(embeddings) != len(texts):
            raise EmbeddingConfigurationError(
                "Embedder returned a different number of vectors than inputs."
            )
        if any(len(vector) != self.embedding_config.dimension for vector in embeddings):
            raise EmbeddingConfigurationError(
                "Embedder output dimension does not match embedding_config.json."
            )
        return embeddings

    def add_document(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        *,
        document_id: str | None = None,
    ) -> str:
        return self.add_documents(
            [text],
            [metadata],
            document_ids=[document_id or str(uuid.uuid4())],
        )[0]

    def add_documents(
        self,
        texts: Sequence[str],
        metadatas: Sequence[dict[str, Any] | None] | None = None,
        *,
        document_ids: Sequence[str] | None = None,
    ) -> list[str]:
        text_list = list(texts)
        metadata_list = (
            [None] * len(text_list) if metadatas is None else list(metadatas)
        )
        id_list = (
            [str(uuid.uuid4()) for _ in text_list]
            if document_ids is None
            else list(document_ids)
        )
        if len(metadata_list) != len(text_list) or len(id_list) != len(text_list):
            raise ValueError("Texts, metadata, and document IDs must have equal lengths.")
        if any(not isinstance(value, str) or not value.strip() for value in text_list):
            raise ValueError("Document text cannot be empty.")
        if not text_list:
            return []
        prepared = [
            _prepare_metadata(value) or {"document_id": identifier}
            for value, identifier in zip(metadata_list, id_list)
        ]
        self.collection.add(
            ids=id_list,
            documents=text_list,
            metadatas=prepared,
            embeddings=self._embed(text_list),
        )
        return id_list

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query cannot be empty.")
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        result_count = min(top_k, self.collection.count())
        if result_count == 0:
            return []
        query_result = self.collection.query(
            query_embeddings=self._embed([query]),
            n_results=result_count,
            include=["documents", "metadatas", "distances"],
        )
        return _format_query_results(query_result)

    def get_document_chunks(self, parent_document: str) -> list[dict[str, Any]]:
        result = self.collection.get(
            where={"parent_document": parent_document},
            include=["documents", "metadatas"],
        )
        return _format_get_results(result)

    def get_all(self) -> list[dict[str, Any]]:
        result = self.collection.get(include=["documents", "metadatas"])
        return _format_get_results(result)

    def count_document_chunks(self, parent_document: str) -> int:
        return len(self.get_document_chunks(parent_document))

    def delete_document(self, document_id: str) -> None:
        """Compatibility deletion by vector/chunk ID."""

        self.collection.delete(ids=[document_id])

    def delete_chunks(self, chunk_ids: Sequence[str]) -> None:
        if chunk_ids:
            self.collection.delete(ids=list(chunk_ids))

    def delete_document_chunks(self, parent_document: str) -> None:
        self.collection.delete(where={"parent_document": parent_document})

    def count(self) -> int:
        return self.collection.count()


def _format_query_results(query_result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = query_result.get("ids", [[]])[0]
    documents = query_result.get("documents", [[]])[0]
    metadatas = query_result.get("metadatas", [[]])[0]
    distances = query_result.get("distances", [[]])[0]
    return [
        {
            "id": identifier,
            "chunk_id": identifier,
            "text": document,
            "document": document,
            "content": document,
            "metadata": _restore_metadata(metadata),
            "distance": float(distance),
            "score": max(-1.0, min(1.0, 1.0 - float(distance))),
        }
        for identifier, document, metadata, distance in zip(
            ids, documents, metadatas, distances
        )
    ]


def _format_get_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = result.get("ids", [])
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])
    return [
        {
            "id": identifier,
            "chunk_id": identifier,
            "text": document,
            "document": document,
            "content": document,
            "metadata": _restore_metadata(metadata),
        }
        for identifier, document, metadata in zip(ids, documents, metadatas)
    ]
