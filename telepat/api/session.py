from __future__ import annotations

from pydantic import BaseModel

from telepat.core.session_manager import session_manager
from telepat.memory.compact import compact_memory
from telepat.memory.remote import remote_memory


class SessionBootstrapRequest(BaseModel):
    user_id: str | None = None
    session_id: str | None = None
    language: str = "ru"


class SessionBootstrapResponse(BaseModel):
    user_id: str
    session_id: str
    language: str
    memory_ready: bool
    astro_ready: bool


async def bootstrap_session(
    request: SessionBootstrapRequest,
) -> SessionBootstrapResponse:
    session = session_manager.get_or_create(
        session_id=request.session_id,
        user_id=request.user_id,
        language=request.language,
    )

    memory_ready = False
    if remote_memory.configured:
        recalled = await remote_memory.recall(
            user_id=session.user_id,
            message="session bootstrap",
            level="simple",
        )
        if recalled:
            session_manager.set_user_memory(
                session.session_id,
                compact_memory(recalled),
            )
            memory_ready = True

    return SessionBootstrapResponse(
        user_id=session.user_id,
        session_id=session.session_id,
        language=session.language,
        memory_ready=memory_ready,
        astro_ready=session.astro_summary is not None,
    )
