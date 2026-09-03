import gc
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_PATH = PROJECT_ROOT / "02_AI_AGENTS"
CORE_PATH = PROJECT_ROOT / "01_CORE_KERNEL"
sys.path.insert(0, str(AGENTS_PATH))
sys.path.insert(0, str(CORE_PATH))

from jarvis import Jarvis
from knowledge_system import KnowledgeManager
from literature_agent.agent import LiteratureAgent


def test_knowledge_manager():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary_directory:
        temporary_path = Path(temporary_directory)
        document_path = temporary_path / "education-study.txt"
        document_path.write_text(
            "Adaptive learning systems use artificial intelligence for student assessment.",
            encoding="utf-8",
        )

        manager = KnowledgeManager(temporary_path / "knowledge")
        ingested = manager.ingest_document(
            document_path,
            tags=["education", "assessment"],
            source="local-test",
        )
        results = manager.search("AI education student assessment")

        assert ingested["filename"] == "education-study.txt"
        assert ingested["metadata"]["document_type"] == "txt"
        assert ingested["chunk_count"] == 1
        assert ingested["duplicate"] is False
        assert len(results) == 1
        assert results[0]["metadata"]["parent_document"] == ingested["id"]
        assert results[0]["metadata"]["tags"] == ["education", "assessment"]
        assert results[0]["metadata"]["source"] == "local-test"

        agent = LiteratureAgent(knowledge=manager)
        agent_result = agent.execute("Analyze AI education assessment papers")
        assert agent_result["knowledge_results"][0]["metadata"][
            "parent_document"
        ] == ingested["id"]
        assert "education-study.txt" in agent_result["response"]

        jarvis = Jarvis(knowledge=manager)
        routed_result = jarvis.process_request("Analyze AI education papers")
        assert routed_result["status"] == "completed"
        assert routed_result["result"]["knowledge_results"][0]["metadata"][
            "parent_document"
        ] == ingested["id"]

        manager.close()
        del manager
        gc.collect()


if __name__ == "__main__":
    test_knowledge_manager()
    print("Knowledge manager test passed.")
