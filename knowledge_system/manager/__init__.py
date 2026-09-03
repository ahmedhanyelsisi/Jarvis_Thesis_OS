"""Knowledge-system orchestration interfaces."""

from .knowledge_manager import KnowledgeManager
from .transaction_manager import (
    KnowledgeConsistencyError,
    KnowledgeTransactionManager,
)

__all__ = [
    "KnowledgeConsistencyError",
    "KnowledgeManager",
    "KnowledgeTransactionManager",
]
