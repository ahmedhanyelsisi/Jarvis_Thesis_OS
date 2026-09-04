# Jarvis Knowledge System

## Purpose

The Knowledge System gives Jarvis persistent, source-aware research retrieval.
It ingests local PDF, DOCX, and TXT documents, stores chunk vectors in Chroma,
catalogs research metadata in SQLite, and preserves reusable topic and paper
memory. It is local-first and has no paid-service dependency.

## Architecture

```text
knowledge_system/
|-- ingestion/             PDF, DOCX, TXT extraction and chunking
|-- database/              Chroma vectors and thread-safe SQLite metadata
|-- retrieval/             Chunk search and metadata enrichment
|-- memory/                Thread-safe topic and paper context
`-- manager/               Public manager and transaction boundary

04_KNOWLEDGE_SYSTEM/
|-- ingestion/             Backward-compatible imports
|-- database/              Backward-compatible imports
|-- retrieval/             Backward-compatible imports
|-- memory/                Backward-compatible imports
|-- knowledge_manager.py   Backward-compatible import
`-- data/                   Generated local state (gitignored)
```

The default embedding backend is `LocalHashEmbedder`, a deterministic lexical
embedder that works entirely offline. `SentenceTransformerEmbedder` is an
opt-in backend for stronger semantic retrieval. It defaults to
`local_files_only=True`, so it will not silently download a model. The active
provider, model, model version, and vector dimension are persisted in
`embedding_config.json` and validated whenever the database is opened.
The default `knowledge.embedding_provider` setting is therefore `local-hash`,
matching the provider used when `KnowledgeManager` is created without an
explicit embedder.

## Data flow

```text
Local document
      |
      v
PDF / DOCX / TXT loader
      |
      v
Overlapping chunks (1000 characters, 200 overlap)
      |
      +------> SQLite metadata catalog
      |
      `------> Local embeddings -----> Chroma collection
                                         |
User or agent query ---------------------+
                                         v
                                  Search Engine
                                         |
                                         v
                          Ranked text + source metadata
```

Each loader returns the same contract:

```python
{
    "filename": "paper.pdf",
    "content": "Extracted document text...",
    "metadata": {"document_type": "pdf", "author": "..."},
}
```

The SQLite catalog stores the document ID, content hash, filename, document
type, author, UTC date added, tags, source, ingestion state, and expected chunk
count. Every Chroma chunk stores its parent document ID and source metadata.
`KnowledgeTransactionManager` uses an atomic SQLite claim and the `PENDING`,
`PROCESSING`, `READY`, and `FAILED` states to coordinate independent manager
instances. It also coordinates duplicate detection, rollback, verified
deletion, and reconciliation between both stores.

## Usage

```python
from knowledge_system import KnowledgeManager


with KnowledgeManager() as manager:
    document = manager.ingest_document(
        "papers/ai-education.pdf",
        tags=["AI", "education", "assessment"],
        source="local-library",
    )
    results = manager.search("AI education assessment", top_k=5)

    manager.memory.remember_topic(
        "AI-supported assessment",
        {"document_id": document["id"]},
    )
    previous_context = manager.memory.get_memory("topic")
```

### Sentence Transformers backend

Use a model already present on disk to retain offline behavior:

```python
from knowledge_system.database import SentenceTransformerEmbedder

embedder = SentenceTransformerEmbedder("models/all-MiniLM-L6-v2")
manager = KnowledgeManager(embedder=embedder)
```

Set `local_files_only=False` explicitly only when downloading a free model is
acceptable. A collection must always be queried with the same embedding model
and dimensions used when its documents were added.

### Agent integration

Knowledge is an optional dependency on the shared base agent. Existing agents
continue to work without it. A knowledge-aware literature flow can be wired
through the kernel as follows:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("01_CORE_KERNEL").resolve()))

from jarvis import Jarvis

knowledge = KnowledgeManager()
jarvis = Jarvis(knowledge=knowledge)
response = jarvis.process_request("Analyze AI education papers")
```

The Literature Agent returns ranked chunks, structured evidence, and a
source-labelled response. Without a Knowledge Manager it retains its original
Stone 3 response exactly. Any agent can use
`self.search_knowledge(query, top_k)` or the injected
`self.knowledge.search(...)` interface.

## Operational notes

- Generated databases live under `04_KNOWLEDGE_SYSTEM/data/` by default.
- `embedding_config.json` prevents a collection from being opened with an
  incompatible provider, model, version, or vector dimension.
- Documents are deduplicated by SHA-256 content hash.
- Concurrent ingestion claims are atomic across independent manager instances;
  non-owners receive a `PROCESSING` response while the owner works.
- Failed ingestion is retained as `FAILED`, cleaned of vectors, and can be
  claimed again by a later retry.
- `manager.delete_document(id)` synchronizes vector and metadata deletion.
- `manager.reconcile()` detects and repairs incomplete or orphaned records.
- Tests and applications can pass a different `storage_path` for isolation.
- Scanned image-only PDFs require a future OCR adapter; `pypdf` extracts only
  embedded text.
- Call `KnowledgeManager.close()` (or use it as a context manager) to close its
  SQLite resources cleanly.
