from __future__ import annotations

import asyncio
from dataclasses import dataclass

from telepat.avatar.director import select_speaking_state
from telepat.avatar.state_selector import select_avatar_state
from telepat.llm.router import llm_router
from telepat.memory.compact import compact_memory
from telepat.memory.service import memory_adapter

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

        if plan.use_memory and memory_adapter.configured:
            recalled = await memory_adapter.recall(
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

        reply, provider_name = await llm_router.generate(context)

        session_manager.append(
            session.session_id,
            "assistant",
            reply,
        )

        if memory_adapter.configured:
            # Persistence is intentionally off the critical response path.
            asyncio.create_task(
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

        return ChatResponse(
            reply=reply,
            user_id=session.user_id,
            session_id=session.session_id,
            intent=plan.intent,
            avatar_state=speaking_state,
            provider=provider_name,
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
