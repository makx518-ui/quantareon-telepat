from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from threading import RLock


@dataclass(slots=True)
class _Bucket:
    window_started: float
    count: int = 0


class FixedWindowRateLimiter:
    """Small in-process limiter for expensive TELEPAT operations.

    Identities are SHA-256 hashed before storage. This is not an authentication
    system; it is a guardrail against accidental loops and basic abuse.
    """

    def __init__(
        self,
        *,
        window_seconds: float = 60.0,
        max_entries: int = 5000,
    ) -> None:
        self.window_seconds = max(1.0, float(window_seconds))
        self.max_entries = max(100, int(max_entries))
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock = RLock()

    @staticmethod
    def _hash(identity: str) -> str:
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]

    def _purge_locked(self, now: float) -> None:
        stale = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.window_started >= self.window_seconds
        ]
        for key in stale:
            self._buckets.pop(key, None)

        if len(self._buckets) <= self.max_entries:
            return

        oldest = sorted(
            self._buckets.items(),
            key=lambda item: item[1].window_started,
        )
        overflow = len(self._buckets) - self.max_entries
        for key, _bucket in oldest[:overflow]:
            self._buckets.pop(key, None)

    def allow(
        self,
        scope: str,
        identity: str,
        *,
        limit: int,
        now: float | None = None,
    ) -> bool:
        if limit <= 0:
            return True

        current = time.monotonic() if now is None else float(now)
        key = (scope, self._hash(identity or "anonymous"))

        with self._lock:
            self._purge_locked(current)
            bucket = self._buckets.get(key)

            if (
                bucket is None
                or current - bucket.window_started >= self.window_seconds
            ):
                self._buckets[key] = _Bucket(
                    window_started=current,
                    count=1,
                )
                return True

            if bucket.count >= limit:
                return False

            bucket.count += 1
            return True

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = FixedWindowRateLimiter(
    window_seconds=float(
        os.getenv("TELEPAT_RATE_LIMIT_WINDOW_SECONDS", "60")
    ),
    max_entries=int(
        os.getenv("TELEPAT_RATE_LIMIT_MAX_ENTRIES", "5000")
    ),
)


def chat_limit() -> int:
    return int(os.getenv("TELEPAT_CHAT_RPM", "30"))


def astro_limit() -> int:
    return int(os.getenv("TELEPAT_ASTRO_RPM", "6"))


def voice_connect_limit() -> int:
    return int(os.getenv("TELEPAT_VOICE_CONNECT_RPM", "12"))
