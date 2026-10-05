from __future__ import annotations

import asyncio
from dataclasses import dataclass

from telepat.llm.router import llm_router
from telepat.memory.compact import compact_memory
from telepat.memory.remote import remote_memory

from .context_builder import build_context_packet, classify_intent
from .models import ChatRequest, ChatResponse
from .plan import OrchestrationPlan, build_plan
from .session_manager import session_manager


@dataclass(slots=True)
class Orchestrator:
    """Central TELEPAT control plane.

    The orchestrator plans and coordinates. It does not implement astrology,
    memory storage, TTS, STT or avatar rendering itself.
    """

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        session = session_manager.get_or_create(
            session_id=request.session_id,
            user_id=request.user_id,
            language=request.language,
        )

        session_manager.append(
            session.session_id,
            "user",
            request.message,
        )

        intent = classify_intent(
            request.message,
            has_astro=session.astro_summary is not None,
        )
        plan = build_plan(intent)

        if plan.use_memory and remote_memory.configured:
            recalled = await remote_memory.recall(
                user_id=session.user_id,
                message=request.message,
                level=self._memory_level(plan),
            )
            if recalled:
                session_manager.set_user_memory(
                    session.session_id,
                    compact_memory(recalled),
                )

        context = build_context_packet(
            session,
            request.message,
            plan,
        )

        provider = llm_router.get()
        reply = await provider.generate(context)

        session_manager.append(
            session.session_id,
            "assistant",
            reply,
        )

        if remote_memory.configured:
            # Persistence is intentionally off the critical response path.
            asyncio.create_task(
                remote_memory.store_exchange(
                    user_id=session.user_id,
                    message=request.message,
                    response_text=reply,
                )
            )

        return ChatResponse(
            reply=reply,
            user_id=session.user_id,
            session_id=session.session_id,
            intent=plan.intent,
            avatar_state=plan.avatar_state,
            provider=provider.name,
        )

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
