from __future__ import annotations

import asyncio
import hashlib
import json
import weakref
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any
from time import perf_counter

from telepat.avatar.director import select_speaking_state
from telepat.avatar.state_selector import select_avatar_state
from telepat.llm.router import llm_router
from telepat.memory.compact import compact_memory
from telepat.memory.service import memory_adapter
from telepat.observability.metrics import runtime_metrics

from .context_builder import build_context_packet, classify_intent
from .models import ChatRequest, ChatResponse
from .plan import OrchestrationPlan, build_plan
from .response_policy import apply_response_policy
from .session_service import session_store


@dataclass(slots=True)
class Orchestrator:
    """Central TELEPAT control plane.

    The orchestrator plans and coordinates. It does not implement astrology,
    memory storage, TTS, STT or avatar rendering itself.
    """

    _background_tasks: set[asyncio.Task[Any]] = field(
        default_factory=set,
        init=False,
        repr=False,
    )
    _session_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary,
        init=False,
        repr=False,
    )
    _session_locks_guard: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        init=False,
        repr=False,
    )

    def _spawn_background(
        self,
        coroutine: Coroutine[Any, Any, Any],
    ) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def drain_background(self) -> None:
        if not self._background_tasks:
            return
        await asyncio.gather(
            *tuple(self._background_tasks),
            return_exceptions=True,
        )

    async def _turn_lock(self, session_id: str) -> asyncio.Lock:
        async with self._session_locks_guard:
            lock = self._session_locks.get(session_id)
            if lock is None:
                lock = asyncio.Lock()
                self._session_locks[session_id] = lock
            return lock

    @staticmethod
    def _request_fingerprint(request: ChatRequest) -> str:
        payload = json.dumps(
            {
                "message": request.message,
                "language": request.language,
                "metadata": request.metadata,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        session = session_store.get_or_create(
            session_id=request.session_id,
            user_id=request.user_id,
            language=request.language,
        )
        lock = await self._turn_lock(session.session_id)

        async with lock:
            return await self._handle_chat_locked(session, request)

    async def _handle_chat_locked(
        self,
        session,
        request: ChatRequest,
    ) -> ChatResponse:
        request_fingerprint = (
            self._request_fingerprint(request)
            if request.request_id
            else None
        )

        if request.request_id and request_fingerprint:
            cached = session_store.get_idempotent_response(
                session.session_id,
                request.request_id,
                request_fingerprint,
            )
            if cached is not None:
                return cached

        started = perf_counter()

        intent = classify_intent(
            request.message,
            has_astro=session.astro_summary is not None,
        )
        plan = build_plan(intent)

        if plan.use_memory and memory_adapter.configured:
            recalled = await memory_adapter.recall(
                user_id=session.user_id,
                message=request.message,
                level=self._memory_level(plan),
            )
            if recalled:
                session_store.set_user_memory(
                    session.session_id,
                    compact_memory(recalled),
                )

        context = build_context_packet(
            session,
            request.message,
            plan,
        )

        try:
            reply, provider_name = await llm_router.generate(context)
            reply = apply_response_policy(reply).text
        except Exception:
            runtime_metrics.record(
                "turn_total",
                (perf_counter() - started) * 1000,
                ok=False,
            )
            raise

        # Commit the exchange only after a real response succeeds. This keeps
        # retries idempotent at the session-history level when a provider is
        # temporarily unavailable.
        session_store.append(
            session.session_id,
            "user",
            request.message,
        )
        session_store.append(
            session.session_id,
            "assistant",
            reply,
        )

        if memory_adapter.configured:
            # Persistence is intentionally off the critical response path.
            self._spawn_background(
                memory_adapter.store_exchange(
                    user_id=session.user_id,
                    message=request.message,
                    response_text=reply,
                )
            )

        speaking_state = select_speaking_state(
            intent=plan.intent,
            user_message=request.message,
            reply=reply,
            session_id=session.session_id,
        )

        runtime_metrics.record(
            "turn_total",
            (perf_counter() - started) * 1000,
            ok=True,
            provider=provider_name,
        )

        response = ChatResponse(
            reply=reply,
            request_id=request.request_id,
            user_id=session.user_id,
            session_id=session.session_id,
            intent=plan.intent,
            avatar_state=speaking_state,
            provider=provider_name,
        )

        if request.request_id and request_fingerprint:
            session_store.set_idempotent_response(
                session.session_id,
                request.request_id,
                request_fingerprint,
                response,
            )

        return response

    @staticmethod
    def _memory_level(plan: OrchestrationPlan) -> str:
        if plan.intent == "factual_user_memory":
            return "deep"
        if plan.intent in {
            "personal_reflection",
            "astropsychology",
            "follow_up_astro",
        }:
            return "medium"
        return "simple"


orchestrator = Orchestrator()
