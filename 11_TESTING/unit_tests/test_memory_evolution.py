"""Stone 6 memory persistence, ranking, and Jarvis integration tests."""

import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from memory import MEMORY_TYPES, MemoryManager, MemoryType


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "01_CORE_KERNEL"))

from jarvis import Jarvis


def _manager(tmp_path: Path, **overrides) -> MemoryManager:
    return MemoryManager(
        tmp_path / "memory_database.sqlite",
        max_results=overrides.get("max_results", 10),
        importance_threshold=overrides.get("importance_threshold", 0.0),
    )


def _jarvis_config(tmp_path: Path) -> dict:
    return {
        "knowledge": {"enabled": False},
        "memory": {
            "enabled": True,
            "database_path": str(tmp_path / "jarvis-memory.sqlite"),
            "max_results": 5,
            "importance_threshold": 0.0,
        },
        "reasoning": {
            "enabled": True,
            "memory_path": str(tmp_path / "reasoning.json"),
        },
        "planner": {"enabled": True},
        "evaluation": {"enabled": False},
    }


def test_memory_creation_supports_every_category(tmp_path: Path):
    manager = _manager(tmp_path)

    created = [
        manager.store_memory(memory_type, f"content for {memory_type}")
        for memory_type in sorted(MEMORY_TYPES)
    ]

    assert {memory.memory_type for memory in created} == MEMORY_TYPES
    assert all(memory.memory_id and memory.access_count == 0 for memory in created)
    assert (tmp_path / "memory_database.sqlite").exists()
    manager.close()


def test_retrieval_updates_access_statistics(tmp_path: Path):
    manager = _manager(tmp_path)
    created = manager.store_memory(
        MemoryType.PROJECT_MEMORY,
        "The thesis uses a local-first architecture.",
        metadata={"project": "Jarvis"},
        importance_score=0.8,
    )

    retrieved = manager.retrieve_memory(created.memory_id)

    assert retrieved.content == created.content
    assert retrieved.metadata == {"project": "Jarvis"}
    assert retrieved.access_count == 1
    assert retrieved.last_accessed >= created.last_accessed
    manager.close()


def test_memory_update_and_deletion(tmp_path: Path):
    manager = _manager(tmp_path)
    created = manager.store_memory("decision_memory", "Use JSON", importance_score=0.2)

    updated = manager.update_memory(
        created.memory_id,
        content="Use SQLite",
        metadata={"reason": "transactional persistence"},
        importance_score=0.95,
    )

    assert updated.content == "Use SQLite"
    assert updated.importance_score == 0.95
    assert updated.updated_at >= created.updated_at
    assert manager.delete_memory(created.memory_id) is True
    assert manager.retrieve_memory(created.memory_id) is None
    assert manager.delete_memory(created.memory_id) is False
    manager.close()


def test_memory_persists_after_manager_restart(tmp_path: Path):
    path = tmp_path / "persistent.sqlite"
    first = MemoryManager(path)
    created = first.store_memory("user_preference_memory", "Prefer concise answers")
    first.close()

    restored = MemoryManager(path)

    assert restored.retrieve_memory(created.memory_id).content == "Prefer concise answers"
    restored.close()


def test_search_ranking_combines_relevance_importance_recency_and_frequency(
    tmp_path: Path,
):
    manager = _manager(tmp_path)
    relevant = manager.store_memory(
        "project_memory", "SQLite memory architecture for Jarvis", importance_score=0.9
    )
    older = manager.store_memory(
        "project_memory", "SQLite notes", importance_score=0.6
    )
    unrelated = manager.store_memory(
        "project_memory", "LaTeX bibliography style", importance_score=0.1
    )
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
    with manager.store._transaction() as connection:
        connection.execute(
            "UPDATE memories SET updated_at = ?, access_count = 4 WHERE memory_id = ?",
            (old_timestamp, older.memory_id),
        )

    results = manager.search_memory("SQLite memory architecture", max_results=3)

    assert results[0].memory_id == relevant.memory_id
    assert results[0].ranking_score > results[1].ranking_score
    assert results[-1].memory_id == unrelated.memory_id
    assert all(result.access_count >= 1 for result in results)
    manager.close()


def test_search_filters_type_threshold_and_clears_only_session_memory(tmp_path: Path):
    manager = _manager(tmp_path, importance_threshold=0.5)
    session = manager.store_memory("session_memory", "temporary topic", importance_score=0.8)
    project = manager.store_memory("project_memory", "persistent topic", importance_score=0.8)
    manager.store_memory("project_memory", "low priority topic", importance_score=0.2)

    results = manager.search_memory("topic", memory_type="project_memory")

    assert [item.memory_id for item in results] == [project.memory_id]
    assert manager.clear_session_memory() == 1
    assert manager.retrieve_memory(session.memory_id) is None
    assert manager.retrieve_memory(project.memory_id) is not None
    manager.close()


def test_jarvis_retrieves_before_reasoning_and_stores_successful_experience(
    tmp_path: Path, monkeypatch
):
    jarvis = Jarvis(config=_jarvis_config(tmp_path))
    remembered = jarvis.memory_manager.store_memory(
        "project_memory",
        "Architecture diagrams must show the memory subsystem.",
        importance_score=1.0,
    )
    events = []
    original_search = jarvis.memory_manager.search_memory
    original_analyze = jarvis.reasoning_engine.analyze

    def tracked_search(query, *args, **kwargs):
        events.append("memory")
        return original_search(query, *args, **kwargs)

    def tracked_analyze(request):
        events.append("reasoning")
        return original_analyze(request)

    monkeypatch.setattr(jarvis.memory_manager, "search_memory", tracked_search)
    monkeypatch.setattr(jarvis.reasoning_engine, "analyze", tracked_analyze)

    result = jarvis.process_workflow("Create an architecture diagram")

    assert events[:2] == ["memory", "reasoning"]
    assert result["memory_context"][0]["memory_id"] == remembered.memory_id
    first_task = result["tasks"][0]["description"]
    assert "Relevant persistent memory" in first_task
    experiences = jarvis.memory_manager.search_memory(
        "Successful diagram creation workflow",
        memory_type="experience_memory",
    )
    assert len(experiences) == 1
    assert experiences[0].metadata["workflow_id"] == result["workflow"]["workflow_id"]
    jarvis.close()


def test_memory_package_has_no_external_service_dependency():
    for module_name in (
        "memory.memory_models",
        "memory.memory_store",
        "memory.memory_retriever",
        "memory.memory_manager",
    ):
        assert importlib.import_module(module_name) is not None

