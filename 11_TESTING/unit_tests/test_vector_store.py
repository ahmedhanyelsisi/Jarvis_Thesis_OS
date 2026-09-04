import gc
import tempfile
from pathlib import Path

from knowledge_system.database import VectorStore


def test_vector_store():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary_directory:
        store = VectorStore(Path(temporary_directory) / "chroma")
        first_id = store.add_document(
            "Neural networks improve artificial intelligence education assessment.",
            {"filename": "ai-education.txt", "tags": ["AI", "education"]},
        )
        store.add_document(
            "Soil moisture influences plant root growth and crop health.",
            {"filename": "plant-biology.txt"},
        )

        results = store.search("neural network education assessment", top_k=2)

        assert store.count() == 2
        assert results[0]["id"] == first_id
        assert results[0]["metadata"]["tags"] == ["AI", "education"]
        assert results[0]["score"] > results[1]["score"]

        del store
        gc.collect()


if __name__ == "__main__":
    test_vector_store()
    print("Vector store test passed.")
