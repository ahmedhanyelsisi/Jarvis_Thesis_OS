"""Deterministic command-center metrics with typed snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from threading import RLock

from .dashboard_models import utc_now


@dataclass(frozen=True)
class DashboardMetricsSnapshot:
    total_requests: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    active_agents: int = 0
    last_execution_time: datetime | None = None
    average_execution_duration: float = 0.0

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        if self.last_execution_time is not None:
            result["last_execution_time"] = self.last_execution_time.isoformat()
        return result


class DashboardMetrics:
    """Thread-safe accumulator for UI-level execution telemetry."""

    def __init__(self) -> None:
        self._snapshot = DashboardMetricsSnapshot()
        self._durations: list[float] = []
        self._lock = RLock()

    def record_request(
        self,
        *,
        workflow: bool = False,
        successful: bool = True,
        duration: float = 0.0,
        active_agents: int = 0,
    ) -> DashboardMetricsSnapshot:
        """Record one command completion and return the updated snapshot."""

        with self._lock:
            duration = max(0.0, float(duration))
            self._durations.append(duration)
            self._snapshot = DashboardMetricsSnapshot(
                total_requests=self._snapshot.total_requests + 1,
                successful_workflows=self._snapshot.successful_workflows
                + int(workflow and successful),
                failed_workflows=self._snapshot.failed_workflows
                + int(workflow and not successful),
                active_agents=max(0, int(active_agents)),
                last_execution_time=utc_now(),
                average_execution_duration=sum(self._durations) / len(self._durations),
            )
            return self._snapshot

    def snapshot(self) -> DashboardMetricsSnapshot:
        with self._lock:
            return self._snapshot

    def to_dict(self) -> dict[str, object]:
        return self.snapshot().to_dict()
