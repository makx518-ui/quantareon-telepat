from __future__ import annotations

import re
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path
from time import perf_counter, time
from typing import Any


_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]{2,}", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text or "")
    }


class SQLiteMemoryStore:
    """Small persistent memory store behind TELEPAT's remote-memory contract."""

    def __init__(
        self,
        path: str | Path,
        *,
        max_exchanges_per_user: int = 240,
        commit_callback: Callable[[], None] | None = None,
    ) -> None:
        self.path = Path(path)
        self.max_exchanges_per_user = max(
            20,
            int(max_exchanges_per_user),
        )
        self.commit_callback = commit_callback
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=20,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS exchanges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_exchanges_user_id
                ON exchanges(user_id, id DESC)
                """
            )
            connection.commit()
        self._persist()

    def _persist(self) -> None:
        if self.commit_callback is not None:
            self.commit_callback()

    def store_exchange(
        self,
        *,
        user_id: int,
        message: str,
        response: str,
    ) -> None:
        message = str(message or "").strip()
        response = str(response or "").strip()
        if not message or not response:
            raise ValueError("message and response must be non-empty")

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO exchanges(user_id, message, response, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (int(user_id), message, response, time()),
            )
            connection.execute(
                """
                DELETE FROM exchanges
                WHERE user_id = ?
                  AND id NOT IN (
                    SELECT id
                    FROM exchanges
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (
                    int(user_id),
                    int(user_id),
                    self.max_exchanges_per_user,
                ),
            )
            connection.commit()
        self._persist()

    def recall(
        self,
        *,
        user_id: int,
        message: str,
        level: str,
    ) -> dict[str, Any]:
        started = perf_counter()
        limits = {
            "simple": 3,
            "medium": 6,
            "deep": 10,
        }
        result_limit = limits.get(str(level or "").lower(), 6)

        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, message, response, created_at
                FROM exchanges
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 100
                """,
                (int(user_id),),
            ).fetchall()

        if not rows:
            return {
                "context_text": "",
                "facts": [],
                "emotion": None,
                "insights": [],
                "semantic_context": [],
                "resonance_context": "",
                "pattern_summary": "",
                "recent_messages": [],
                "recall_ms": round(
                    (perf_counter() - started) * 1000,
                    2,
                ),
            }

        query = _tokens(message)
        newest_id = max(int(row["id"]) for row in rows)

        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            combined = f'{row["message"]} {row["response"]}'
            terms = _tokens(combined)
            overlap = len(query & terms)
            coverage = overlap / max(1, len(query))
            recency = int(row["id"]) / max(1, newest_id)
            score = coverage * 0.82 + recency * 0.18
            if overlap or len(scored) < result_limit:
                scored.append((score, row))

        selected = sorted(
            scored,
            key=lambda item: item[0],
            reverse=True,
        )[:result_limit]

        context_parts = [
            (
                f'User: {row["message"]}\n'
                f'Assistant: {row["response"]}'
            )
            for _score, row in selected
        ]

        semantic_context = [
            {
                "text": (
                    f'User: {row["message"]}\n'
                    f'Assistant: {row["response"]}'
                ),
                "score": round(score, 4),
            }
            for score, row in selected[:5]
        ]

        recent_rows = list(reversed(rows[:5]))
        recent_messages: list[dict[str, str]] = []
        for row in recent_rows:
            recent_messages.extend(
                [
                    {
                        "role": "user",
                        "content": str(row["message"]),
                    },
                    {
                        "role": "assistant",
                        "content": str(row["response"]),
                    },
                ]
            )

        return {
            "context_text": "\n\n".join(context_parts),
            "facts": [],
            "emotion": None,
            "insights": [],
            "semantic_context": semantic_context,
            "resonance_context": "",
            "pattern_summary": (
                f"Persistent exchanges available: {len(rows)}"
            ),
            "recent_messages": recent_messages,
            "recall_ms": round(
                (perf_counter() - started) * 1000,
                2,
            ),
        }
