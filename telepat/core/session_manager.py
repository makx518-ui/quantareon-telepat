from __future__ import annotations

from threading import RLock
from uuid import uuid4

from .models import ConversationTurn, SessionState


class SessionManager:
    """In-process session store for Phase 1.

    This intentionally has the same outward responsibility that the future
    remote memory-backed implementation will keep. Replacing storage later
    must not require changing the orchestrator.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = RLock()

    def get_or_create(
        self,
        *,
        session_id: str | None,
        user_id: str | None,
        language: str,
    ) -> SessionState:
        with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if language:
                    session.language = language
                return session

            session = SessionState(
                session_id=session_id or str(uuid4()),
                user_id=user_id or str(uuid4()),
                language=language or "ru",
            )
            self._sessions[session.session_id] = session
            return session

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            session = self._sessions[session_id]
            session.history.append(ConversationTurn(role=role, content=content))

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._sessions.get(session_id)


session_manager = SessionManager()
