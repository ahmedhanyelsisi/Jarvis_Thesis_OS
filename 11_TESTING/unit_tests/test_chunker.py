from pathlib import Path

from knowledge_system import KnowledgeManager
from knowledge_system.ingestion import DocumentChunker


def test_long_documents_create_overlapping_chunks_with_metadata():
    chunker = DocumentChunker(chunk_size=1000, overlap=200)
    content = "A" * 2500

    for document_type in ("pdf", "docx", "txt"):
        chunks = chunker.split_document(
            {
                "filename": f"research.{document_type}",
                "content": content,
                "metadata": {
                    "document_type": document_type,
                    "author": "Researcher",
                },
            },
            parent_document=f"parent-{document_type}",
        )

        assert len(chunks) == 3
        assert chunks[0]["content"][-200:] == chunks[1]["content"][:200]
        assert chunks[1]["content"][-200:] == chunks[2]["content"][:200]
        assert all(chunk["metadata"]["author"] == "Researcher" for chunk in chunks)
        assert all(
            chunk["parent_document"] == f"parent-{document_type}"
            for chunk in chunks
        )
        assert len({chunk["chunk_id"] for chunk in chunks}) == 3


def test_retrieval_returns_the_relevant_chunk(tmp_path: Path):
    source = tmp_path / "long-paper.txt"
    source.write_text(
        ("introductory background " * 12)
        + ("photosynthesis chlorophyll sunlight " * 8)
        + ("unrelated conclusion " * 12),
        encoding="utf-8",
    )
    manager = KnowledgeManager(
        tmp_path / "knowledge",
        chunk_size=180,
        chunk_overlap=30,
    )
    ingested = manager.ingest_document(source, tags=["biology"])
    results = manager.search("photosynthesis chlorophyll sunlight", top_k=2)

    assert ingested["chunk_count"] > 1
    assert "photosynthesis" in results[0]["content"]
    assert results[0]["metadata"]["parent_document"] == ingested["id"]
    assert results[0]["metadata"]["tags"] == ["biology"]
    manager.close()
