"""Integration coverage for Stone 4 knowledge and Stone 5 orchestration."""

import sys
from pathlib import Path

import pytest

from knowledge_system import KnowledgeManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "01_CORE_KERNEL"))

from jarvis import Jarvis


def _config(memory_path: Path, **evaluation):
    return {
        "knowledge": {"enabled": False},
        "reasoning": {
            "enabled": True,
            "memory_path": str(memory_path),
        },
        "planner": {"enabled": True},
        "evaluation": {
            "enabled": True,
            "quality_threshold": 10,
            "max_improvement_iterations": 1,
            **evaluation,
        },
    }


def test_workflow_retrieves_stone_4_knowledge_and_improves_artifact(tmp_path: Path):
    source = tmp_path / "methodology-reference.txt"
    source.write_text(
        "A mixed-methods methodology combines quantitative experiments with "
        "qualitative interviews and triangulates the resulting evidence.",
        encoding="utf-8",
    )
    knowledge = KnowledgeManager(tmp_path / "knowledge")
    knowledge.ingest_document(source)
    jarvis = Jarvis(
        knowledge=knowledge,
        config=_config(tmp_path / "reasoning.json"),
    )

    result = jarvis.process_workflow(
        "Create a methodology chapter outline with literature references and LaTeX structure"
    )

    literature_output = result["workflow"]["outputs"]["task-2"]["result"]
    writer_output = result["workflow"]["outputs"]["task-3"]["result"]
    assert literature_output["knowledge_results"]
    assert literature_output["evidence"][0]["filename"] == source.name
    assert writer_output["agent"] == "thesis_writer_agent"
    assert result["final_response"]["agent"] == "latex_agent"
    assert result["final_response"] != result["workflow"]["outputs"]["task-4"]
    improvement_task = result["final_response"]["result"]["task"]
    assert "Reviewer feedback:" in improvement_task
    assert "reviewer_agent" in improvement_task
    knowledge.close()


def test_runtime_configuration_controls_stone_5(tmp_path: Path):
    memory_path = tmp_path / "configured-reasoning.json"
    config = _config(
        memory_path,
        enabled=False,
        quality_threshold=9,
        max_improvement_iterations=0,
    )
    jarvis = Jarvis(config=config)

    result = jarvis.process_workflow("Create architecture diagram")

    assert jarvis.reasoning_memory.path == memory_path
    assert jarvis.evaluation_loop.quality_threshold == 9
    assert jarvis.max_improvement_iterations == 0
    assert result["evaluation"] is None
    assert result["final_response"]["agent"] == "diagram_agent"
    assert memory_path.exists()


def test_disabled_reasoning_prevents_workflow_execution(tmp_path: Path):
    config = _config(tmp_path / "unused.json")
    config["reasoning"]["enabled"] = False
    jarvis = Jarvis(config=config)

    with pytest.raises(RuntimeError, match="disabled"):
        jarvis.process_workflow("Write a methodology chapter")


def test_enabled_knowledge_configuration_builds_stone_4_manager(tmp_path: Path):
    config = _config(tmp_path / "reasoning.json")
    config["knowledge"] = {
        "enabled": True,
        "storage_path": str(tmp_path / "configured-knowledge"),
    }

    jarvis = Jarvis(config=config)

    assert isinstance(jarvis.knowledge, KnowledgeManager)
    assert jarvis.knowledge.storage_path == (tmp_path / "configured-knowledge").resolve()
    jarvis.close()
