from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import weakref

from pydantic import BaseModel

from telepat.astro.models import AstroSummary, BirthData
from telepat.astro.service import astro_service
from telepat.core.models import SessionState
from telepat.core.session_manager import session_manager
from telepat.memory.compact import compact_memory
from telepat.memory.service import memory_adapter


logger = logging.getLogger(__name__)

_astro_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = (
    weakref.WeakValueDictionary()
)
_astro_locks_guard = asyncio.Lock()


async def _astro_lock(session_id: str) -> asyncio.Lock:
    async with _astro_locks_guard:
        lock = _astro_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            _astro_locks[session_id] = lock
        return lock


class SessionBootstrapRequest(BaseModel):
    user_id: str | None = None
    session_id: str | None = None
    language: str = "ru"
    birth: BirthData | None = None


class SessionBootstrapResponse(BaseModel):
    user_id: str
    session_id: str
    language: str
    memory_ready: bool
    astro_ready: bool
    astro_status: str


def _birth_fingerprint(birth: BirthData) -> str:
    payload = json.dumps(
        birth.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


async def _bootstrap_memory(session: SessionState) -> bool:
    if not memory_adapter.configured:
        return bool(session.user_memory)

    recalled = await memory_adapter.recall(
        user_id=session.user_id,
        message="session bootstrap",
        level="simple",
    )
    if not recalled:
        return bool(session.user_memory)

    memory = compact_memory(recalled)
    session_manager.set_user_memory(session.session_id, memory)
    return bool(memory)


async def prepare_session_astro(
    *,
    session_id: str,
    birth: BirthData,
    language: str,
) -> tuple[AstroSummary, bool]:
    """Prepare AstroSummary once and reuse it for the same birth profile.

    Returns (summary, cached).
    """
    lock = await _astro_lock(session_id)
    async with lock:
        # Re-read inside the lock: a concurrent request may have completed
        # Astro preparation while this request was waiting.
        session = session_manager.get(session_id)
        if session is None:
            raise RuntimeError("TELEPAT session does not exist")

        fingerprint = _birth_fingerprint(birth)
        cached_fingerprint = session.metadata.get(
            "astro_birth_fingerprint"
        )

        if (
            session.astro_summary is not None
            and cached_fingerprint == fingerprint
        ):
            return AstroSummary.model_validate(
                session.astro_summary
            ), True

        _calculation, summary = await astro_service.calculate_and_interpret(
            birth,
            language=language,
        )

        session_manager.set_astro_summary(
            session_id,
            summary.as_context(),
        )
        session_manager.update_metadata(
            session_id,
            astro_birth_fingerprint=fingerprint,
            astro_provider=summary.provider,
        )
        return summary, False


async def bootstrap_session(
    request: SessionBootstrapRequest,
) -> SessionBootstrapResponse:
    session = session_manager.get_or_create(
        session_id=request.session_id,
        user_id=request.user_id,
        language=request.language,
    )

    memory_task = asyncio.create_task(_bootstrap_memory(session))
    astro_task = None

    if request.birth is not None:
        astro_task = asyncio.create_task(
            prepare_session_astro(
                session_id=session.session_id,
                birth=request.birth,
                language=session.language,
            )
        )

    memory_ready = await memory_task

    if astro_task is None:
        astro_ready = session.astro_summary is not None
        astro_status = "cached" if astro_ready else "missing_birth"
    else:
        try:
            _summary, cached = await astro_task
            astro_ready = True
            astro_status = "cached" if cached else "ready"
        except Exception as exc:
            logger.warning(
                "Astro bootstrap unavailable: %s",
                type(exc).__name__,
            )
            astro_ready = session.astro_summary is not None
            astro_status = "cached" if astro_ready else "unavailable"

    return SessionBootstrapResponse(
        user_id=session.user_id,
        session_id=session.session_id,
        language=session.language,
        memory_ready=memory_ready,
        astro_ready=astro_ready,
        astro_status=astro_status,
    )
