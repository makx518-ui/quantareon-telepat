from __future__ import annotations

import os
import time
from collections import OrderedDict
from collections.abc import Callable
from threading import RLock
from uuid import uuid4

from .models import ChatResponse, ConversationTurn, SessionState


class SessionManager:
    kind = "in_process"

    """Bounded in-process session store for the current TELEPAT MVP.

    The interface stays storage-agnostic so a shared store can replace this
    implementation later without changing the orchestrator.

    Current safeguards:
    - stale sessions expire automatically;
    - session count is bounded;
    - conversation history is bounded;
    - a session_id cannot be reused with a different user_id.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float | None = None,
        max_sessions: int | None = None,
        max_history_turns: int | None = None,
        max_idempotency_entries: int | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.ttl_seconds = float(
            ttl_seconds
            if ttl_seconds is not None
            else os.getenv("TELEPAT_SESSION_TTL_SECONDS", "21600")
        )
        self.max_sessions = int(
            max_sessions
            if max_sessions is not None
            else os.getenv("TELEPAT_MAX_SESSIONS", "1000")
        )
        self.max_history_turns = int(
            max_history_turns
            if max_history_turns is not None
            else os.getenv("TELEPAT_MAX_HISTORY_TURNS", "60")
        )
        self.max_idempotency_entries = int(
            max_idempotency_entries
            if max_idempotency_entries is not None
            else os.getenv("TELEPAT_IDEMPOTENCY_ENTRIES", "32")
        )

        self._clock = clock or time.monotonic
        self._sessions: dict[str, SessionState] = {}
        self._last_seen: dict[str, float] = {}
        self._responses: dict[
            str,
            OrderedDict[str, ChatResponse],
        ] = {}
        self._lock = RLock()

    def _touch_locked(self, session_id: str) -> None:
        self._last_seen[session_id] = self._clock()

    def _delete_locked(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._last_seen.pop(session_id, None)
        self._responses.pop(session_id, None)

    def _purge_stale_locked(self) -> None:
        if self.ttl_seconds <= 0:
            return

        now = self._clock()
        stale = [
            session_id
            for session_id, last_seen in self._last_seen.items()
            if now - last_seen > self.ttl_seconds
        ]
        for session_id in stale:
            self._delete_locked(session_id)

    def _make_room_locked(self) -> None:
        if self.max_sessions <= 0:
            return

        while len(self._sessions) >= self.max_sessions:
            oldest = min(
                self._last_seen,
                key=self._last_seen.get,
                default=None,
            )
            if oldest is None:
                break
            self._delete_locked(oldest)

    def get_or_create(
        self,
        *,
        session_id: str | None,
        user_id: str | None,
        language: str,
    ) -> SessionState:
        with self._lock:
            self._purge_stale_locked()

            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]

                # Reusing an existing session requires both identifiers.
                # session_id alone is not treated as authorization to attach
                # to state that belongs to another browser identity.
                if not user_id or session.user_id != user_id:
                    session_id = None
                else:
                    if language:
                        session.language = language
                    self._touch_locked(session.session_id)
                    return session

            self._make_room_locked()
            session = SessionState(
                session_id=session_id or str(uuid4()),
                user_id=user_id or str(uuid4()),
                language=language or "ru",
            )
            self._sessions[session.session_id] = session
            self._touch_locked(session.session_id)
            return session

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            session = self._sessions[session_id]
            session.history.append(
                ConversationTurn(role=role, content=content)
            )
            if (
                self.max_history_turns > 0
                and len(session.history) > self.max_history_turns
            ):
                del session.history[:-self.max_history_turns]
            self._touch_locked(session_id)

    def set_astro_summary(
        self,
        session_id: str,
        summary: dict,
    ) -> None:
        with self._lock:
            self._sessions[session_id].astro_summary = summary
            self._touch_locked(session_id)

    def set_user_memory(
        self,
        session_id: str,
        memory: dict,
    ) -> None:
        with self._lock:
            self._sessions[session_id].user_memory = memory
            self._touch_locked(session_id)

    def update_metadata(
        self,
        session_id: str,
        **values: object,
    ) -> None:
        with self._lock:
            self._sessions[session_id].metadata.update(values)
            self._touch_locked(session_id)

    def get_idempotent_response(
        self,
        session_id: str,
        request_id: str,
    ) -> ChatResponse | None:
        with self._lock:
            bucket = self._responses.get(session_id)
            if not bucket:
                return None
            response = bucket.get(request_id)
            if response is not None:
                bucket.move_to_end(request_id)
                self._touch_locked(session_id)
            return response

    def set_idempotent_response(
        self,
        session_id: str,
        request_id: str,
        response: ChatResponse,
    ) -> None:
        if self.max_idempotency_entries <= 0:
            return

        with self._lock:
            bucket = self._responses.setdefault(
                session_id,
                OrderedDict(),
            )
            bucket[request_id] = response
            bucket.move_to_end(request_id)

            while len(bucket) > self.max_idempotency_entries:
                bucket.popitem(last=False)

            self._touch_locked(session_id)

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            self._purge_stale_locked()
            session = self._sessions.get(session_id)
            if session is not None:
                self._touch_locked(session_id)
            return session

    def count(self) -> int:
        with self._lock:
            self._purge_stale_locked()
            return len(self._sessions)


session_manager = SessionManager()
