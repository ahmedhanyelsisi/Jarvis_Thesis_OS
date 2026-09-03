import sys
from pathlib import Path

from knowledge_system import KnowledgeManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "02_AI_AGENTS"))

from literature_agent.agent import LiteratureAgent


def test_literature_workflow_without_knowledge_is_unchanged():
    result = LiteratureAgent().execute("Analyze AI education papers")

    assert result == {
        "agent": "literature_agent",
        "task": "Analyze AI education papers",
        "response": "Literature analysis module activated.",
    }


def test_literature_workflow_with_knowledge_returns_evidence(tmp_path: Path):
    source = tmp_path / "assessment-study.txt"
    source.write_text(
        "Formative assessment with adaptive AI can provide timely student feedback.",
        encoding="utf-8",
    )
    manager = KnowledgeManager(tmp_path / "knowledge")
    ingested = manager.ingest_document(source)

    result = LiteratureAgent(knowledge=manager).execute(
        "Analyze adaptive AI formative assessment"
    )

    assert result["knowledge_results"]
    assert result["evidence"][0]["parent_document"] == ingested["id"]
    assert "assessment-study.txt" in result["response"]
    assert "formative assessment" in result["response"].lower()
    manager.close()
