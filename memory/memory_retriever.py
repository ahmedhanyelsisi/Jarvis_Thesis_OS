"""Deterministic, dependency-free memory retrieval and ranking."""

from __future__ import annotations

import math
import re
from dataclasses import replace
from datetime import datetime, timezone

from .memory_models import MemoryRecord
from .memory_store import MemoryStore


class MemoryRetriever:
    """Rank memories by relevance, importance, recency, and use frequency."""

    RELEVANCE_WEIGHT = 0.50
    IMPORTANCE_WEIGHT = 0.25
    RECENCY_WEIGHT = 0.15
    FREQUENCY_WEIGHT = 0.10
    RECENCY_HALF_LIFE_DAYS = 30.0

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def search(
        self,
        query: str,
        *,
        memory_type: str | None = None,
        max_results: int = 10,
        importance_threshold: float = 0.0,
    ) -> list[MemoryRecord]:
        if not isinstance(query, str):
            raise TypeError("Memory search query must be a string.")
        candidates = self.store.list_candidates(
            memory_type=memory_type,
            importance_threshold=importance_threshold,
        )
        if not candidates or max_results <= 0:
            return []

        max_access = max((record.access_count for record in candidates), default=0)
        now = datetime.now(timezone.utc)
        ranked: list[MemoryRecord] = []
        for record in candidates:
            relevance = self._relevance(query, record)
            recency = self._recency(record.updated_at, now)
            frequency = self._frequency(record.access_count, max_access)
            score = (
                self.RELEVANCE_WEIGHT * relevance
                + self.IMPORTANCE_WEIGHT * record.importance_score
                + self.RECENCY_WEIGHT * recency
                + self.FREQUENCY_WEIGHT * frequency
            )
            ranked.append(
                replace(
                    record,
                    relevance_score=round(relevance, 6),
                    ranking_score=round(score, 6),
                )
            )

        ranked.sort(
            key=lambda item: (
                item.ranking_score or 0.0,
                item.importance_score,
                item.updated_at,
                item.memory_id,
            ),
            reverse=True,
        )
        results = ranked[:max_results]
        accessed_at = self.store.touch_many([item.memory_id for item in results])
        return [
            replace(item, last_accessed=accessed_at, access_count=item.access_count + 1)
            for item in results
        ]

    @classmethod
    def _relevance(cls, query: str, record: MemoryRecord) -> float:
        query_tokens = cls._tokens(query)
        searchable = f"{record.content} {' '.join(map(str, record.metadata.values()))}"
        content_tokens = cls._tokens(searchable)
        if not query_tokens:
            return 1.0
        if not content_tokens:
            return 0.0
        overlap = len(query_tokens & content_tokens)
        precision = overlap / len(content_tokens)
        recall = overlap / len(query_tokens)
        token_score = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        phrase_bonus = 0.2 if query.strip().casefold() in searchable.casefold() else 0.0
        return min(1.0, token_score + phrase_bonus)

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return set(re.findall(r"[\w'-]+", value.casefold(), flags=re.UNICODE))

    @classmethod
    def _recency(cls, updated_at: datetime, now: datetime) -> float:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - updated_at).total_seconds() / 86400.0)
        return math.exp(-math.log(2.0) * age_days / cls.RECENCY_HALF_LIFE_DAYS)

    @staticmethod
    def _frequency(access_count: int, max_access: int) -> float:
        if max_access <= 0:
            return 0.0
        return math.log1p(access_count) / math.log1p(max_access)

