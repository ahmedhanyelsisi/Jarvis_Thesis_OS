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
