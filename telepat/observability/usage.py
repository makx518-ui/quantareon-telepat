from __future__ import annotations

import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from threading import RLock
from collections.abc import Callable
from typing import Any

from telepat.llm.base import ProviderUsage


@dataclass(slots=True)
class _SessionUsage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    thought_tokens: int = 0
    priced_cost_usd: float = 0.0
    priced_calls: int = 0
    unpriced_calls: int = 0
    providers: Counter[str] = field(default_factory=Counter)
    models: Counter[str] = field(default_factory=Counter)
    updated_at: float = field(default_factory=time.monotonic)


class UsageRegistry:
    """Bounded per-session LLM usage/cost accounting.

    No prompts, transcripts, user ids, birth data or model outputs are stored.
    Cost rates are USD per one million tokens and must be explicitly supplied
    in TELEPAT_COST_RATES_JSON.
    """

    def __init__(
        self,
        *,
        max_sessions: int | None = None,
        rates: dict[str, dict[str, float]] | None = None,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.max_sessions = int(
            max_sessions
            if max_sessions is not None
            else os.getenv("TELEPAT_USAGE_MAX_SESSIONS", "5000")
        )
        self.max_sessions = max(100, self.max_sessions)
        self.ttl_seconds = float(
            ttl_seconds
            if ttl_seconds is not None
            else os.getenv(
                "TELEPAT_USAGE_TTL_SECONDS",
                os.getenv("TELEPAT_SESSION_TTL_SECONDS", "21600"),
            )
        )
        self._clock = clock or time.monotonic
        self._rates = rates if rates is not None else self._load_rates()
        self._sessions: dict[str, _SessionUsage] = {}
        self._lock = RLock()

    @staticmethod
    def _load_rates() -> dict[str, dict[str, float]]:
        raw = os.getenv("TELEPAT_COST_RATES_JSON", "").strip()
        if not raw:
            return {}

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}

        if not isinstance(data, dict):
            return {}

        result: dict[str, dict[str, float]] = {}
        for model, values in data.items():
            if not isinstance(values, dict):
                continue
            parsed: dict[str, float] = {}
            for key in (
                "input",
                "cached_input",
                "cache_write",
                "output",
                "thought",
            ):
                try:
                    value = float(values.get(key, 0))
                except (TypeError, ValueError):
                    value = 0.0
                if value >= 0:
                    parsed[key] = value
            result[str(model)] = parsed
        return result

    def _purge_stale_locked(self) -> None:
        if self.ttl_seconds <= 0:
            return

        now = self._clock()
        stale = [
            session_id
            for session_id, item in self._sessions.items()
            if now - item.updated_at > self.ttl_seconds
        ]
        for session_id in stale:
            self._sessions.pop(session_id, None)

    def _make_room_locked(self) -> None:
        if len(self._sessions) < self.max_sessions:
            return

        oldest = min(
            self._sessions,
            key=lambda sid: self._sessions[sid].updated_at,
            default=None,
        )
        if oldest is not None:
            self._sessions.pop(oldest, None)

    def _cost(
        self,
        *,
        model: str,
        usage: ProviderUsage,
    ) -> float | None:
        if model == "mock":
            return 0.0

        rates = self._rates.get(model)
        if not rates:
            return None

        # Provider adapters normalize usage before it reaches this registry:
        # input_tokens = uncached input, cached_input_tokens = cache read,
        # cache_write_input_tokens = cache creation/write. Therefore cost
        # accounting never guesses whether a vendor total includes cache hits.
        thought_rate = rates.get(
            "thought",
            rates.get("output", 0.0),
        )

        cost = (
            max(0, usage.input_tokens) * rates.get("input", 0.0)
            + max(0, usage.cached_input_tokens) * rates.get(
                "cached_input",
                rates.get("input", 0.0),
            )
            + max(0, usage.cache_write_input_tokens) * rates.get(
                "cache_write",
                rates.get("input", 0.0),
            )
            + max(0, usage.output_tokens) * rates.get("output", 0.0)
            + max(0, usage.thought_tokens) * thought_rate
        ) / 1_000_000
        return cost

    def record(
        self,
        session_id: str,
        *,
        provider: str,
        model: str,
        usage: ProviderUsage,
    ) -> None:
        if not session_id:
            return

        with self._lock:
            self._purge_stale_locked()
            item = self._sessions.get(session_id)
            if item is None:
                self._make_room_locked()
                item = _SessionUsage(updated_at=self._clock())
                self._sessions[session_id] = item

            item.calls += 1
            item.input_tokens += max(0, usage.input_tokens)
            item.output_tokens += max(0, usage.output_tokens)
            item.cached_input_tokens += max(
                0,
                usage.cached_input_tokens,
            )
            item.cache_write_input_tokens += max(
                0,
                usage.cache_write_input_tokens,
            )
            item.thought_tokens += max(0, usage.thought_tokens)
            item.providers[provider] += 1
            item.models[model] += 1
            item.updated_at = self._clock()

            cost = self._cost(model=model, usage=usage)
            if cost is None:
                item.unpriced_calls += 1
            else:
                item.priced_calls += 1
                item.priced_cost_usd += cost

    def snapshot(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._purge_stale_locked()
            item = self._sessions.get(session_id)
            if item is None:
                return None

            total_tokens = (
                item.input_tokens
                + item.cached_input_tokens
                + item.cache_write_input_tokens
                + item.output_tokens
                + item.thought_tokens
            )
            return {
                "calls": item.calls,
                "input_tokens": item.input_tokens,
                "output_tokens": item.output_tokens,
                "cached_input_tokens": item.cached_input_tokens,
                "cache_write_input_tokens": item.cache_write_input_tokens,
                "thought_tokens": item.thought_tokens,
                "total_tokens": total_tokens,
                "providers": dict(item.providers),
                "models": dict(item.models),
                "priced_calls": item.priced_calls,
                "unpriced_calls": item.unpriced_calls,
                "fully_priced": (
                    item.calls > 0
                    and item.unpriced_calls == 0
                ),
                "priced_cost_usd": round(item.priced_cost_usd, 8),
            }

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()


usage_registry = UsageRegistry()
