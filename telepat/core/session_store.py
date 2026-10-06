from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import ChatResponse, SessionState


@runtime_checkable
class SessionStore(Protocol):
    """Stable TELEPAT session-state boundary.

    The current implementation is in-process. A shared Redis/Postgres/other
    store can replace it later without changing API/orchestration callers.
    """

    kind: str
    ttl_seconds: float
    max_sessions: int
    max_history_turns: int
    max_idempotency_entries: int

    def get_or_create(
        self,
        *,
        session_id: str | None,
        user_id: str | None,
        language: str,
    ) -> SessionState: ...

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None: ...

    def set_astro_summary(
        self,
        session_id: str,
        summary: dict,
    ) -> None: ...

    def set_user_memory(
        self,
        session_id: str,
        memory: dict,
    ) -> None: ...

    def update_metadata(
        self,
        session_id: str,
        **values: object,
    ) -> None: ...

    def get_idempotent_response(
        self,
        session_id: str,
        request_id: str,
    ) -> ChatResponse | None: ...

    def set_idempotent_response(
        self,
        session_id: str,
        request_id: str,
        response: ChatResponse,
    ) -> None: ...

    def get(self, session_id: str) -> SessionState | None: ...

    def count(self) -> int: ...
