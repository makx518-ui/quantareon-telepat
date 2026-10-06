from __future__ import annotations

import os
from collections import Counter, deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Any


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            int(round((len(ordered) - 1) * fraction)),
        ),
    )
    return ordered[index]


@dataclass(slots=True)
class _Stage:
    sample_limit: int
    durations_ms: deque[float] = field(init=False)
    count: int = 0
    errors: int = 0
    providers: Counter[str] = field(default_factory=Counter)

    def __post_init__(self) -> None:
        self.durations_ms = deque(maxlen=self.sample_limit)

    def record(
        self,
        duration_ms: float,
        *,
        ok: bool,
        provider: str | None,
    ) -> None:
        self.count += 1
        if not ok:
            self.errors += 1
        self.durations_ms.append(max(0.0, float(duration_ms)))
        if provider:
            self.providers[str(provider)] += 1

    def snapshot(self) -> dict[str, Any]:
        values = list(self.durations_ms)
        successes = self.count - self.errors
        return {
            "count": self.count,
            "errors": self.errors,
            "success_rate": round(
                successes / self.count if self.count else 1.0,
                4,
            ),
            "avg_ms": round(
                sum(values) / len(values) if values else 0.0,
                2,
            ),
            "p50_ms": round(_percentile(values, 0.50), 2),
            "p95_ms": round(_percentile(values, 0.95), 2),
            "max_ms": round(max(values) if values else 0.0, 2),
            "sample_size": len(values),
            "providers": dict(self.providers),
        }


class MetricsRegistry:
    """Small in-process metrics registry with bounded latency samples.

    It deliberately stores no prompt, transcript, user id, session id,
    birth data or other user content.
    """

    def __init__(self, sample_limit: int | None = None) -> None:
        self.sample_limit = int(
            sample_limit
            if sample_limit is not None
            else os.getenv("TELEPAT_METRICS_SAMPLE_LIMIT", "200")
        )
        self.sample_limit = max(10, self.sample_limit)
        self._stages: dict[str, _Stage] = {}
        self._lock = RLock()

    def record(
        self,
        stage: str,
        duration_ms: float,
        *,
        ok: bool = True,
        provider: str | None = None,
    ) -> None:
        name = str(stage).strip().lower()
        if not name:
            return

        with self._lock:
            item = self._stages.get(name)
            if item is None:
                item = _Stage(self.sample_limit)
                self._stages[name] = item
            item.record(duration_ms, ok=ok, provider=provider)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                name: stage.snapshot()
                for name, stage in sorted(self._stages.items())
            }

    def reset(self) -> None:
        with self._lock:
            self._stages.clear()


runtime_metrics = MetricsRegistry()
