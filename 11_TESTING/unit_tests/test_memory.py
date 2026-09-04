import tempfile
from pathlib import Path

from knowledge_system.memory import ResearchMemory


def test_research_memory():
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "memory.sqlite3"
        memory = ResearchMemory(database_path)
        memory.remember_topic("AI in education", {"stage": "literature review"})
        memory.remember_paper(
            {"title": "Intelligent Tutoring Systems", "year": 2025},
            {"status": "reviewed"},
        )
        memory.close()

        reopened_memory = ResearchMemory(database_path)
        records = reopened_memory.get_memory()

        assert len(records) == 2
        assert reopened_memory.get_memory("topic")[0]["value"] == "AI in education"
        assert reopened_memory.get_memory("paper")[0]["value"]["year"] == 2025
        assert reopened_memory.clear_memory("topic") == 1
        assert len(reopened_memory.get_memory()) == 1
        assert reopened_memory.clear_memory() == 1
        assert reopened_memory.get_memory() == []
        reopened_memory.close()


if __name__ == "__main__":
    test_research_memory()
    print("Research memory test passed.")
