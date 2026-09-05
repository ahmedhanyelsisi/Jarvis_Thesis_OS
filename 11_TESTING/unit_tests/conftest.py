import gc
import pytest

@pytest.fixture(autouse=True)
def force_garbage_collection_for_windows_locks():
    """
    Forces garbage collection after every test.
    This ensures that instances of KnowledgeManager, ChromaDB, and SQLite
    connections that were not explicitly closed by frozen Stone tests
    are garbage collected. This releases file handles and prevents
    PermissionError (WinError 32) when pytest attempts to clean up tmp_path.
    """
    yield
    gc.collect()

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '02_AI_AGENTS', 'legacy')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '05_LATEX_ENGINE')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '06_BUILD_ORCHESTRATION')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '07_THESIS_INTELLIGENCE')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '08_THESIS_SESSION')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '09_THESIS_KNOWLEDGE')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '10_ACADEMIC_AGENTS')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '11_WORKFLOW_ORCHESTRATOR')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '12_ACADEMIC_QUALITY')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '20_RESEARCH_INTELLIGENCE')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '21_THESIS_REASONING')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '13_ACADEMIC_MEMORY')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '14_THESIS_PIPELINE')))
