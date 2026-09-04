from pathlib import Path

import yaml

from knowledge_system import KnowledgeManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_knowledge_configuration_matches_runtime(tmp_path: Path):
    config = yaml.safe_load(
        (PROJECT_ROOT / "jarvis_config.yaml").read_text(encoding="utf-8")
    )

    assert config["ai"]["provider"] == "local"
    assert config["knowledge"] == {
        "enabled": True,
        "vector_database": "chromadb",
        "embedding_provider": "local-hash",
    }
    manager = KnowledgeManager(tmp_path / "knowledge")
    assert (
        manager.vector_store.embedding_config.provider
        == config["knowledge"]["embedding_provider"]
    )
    manager.close()
