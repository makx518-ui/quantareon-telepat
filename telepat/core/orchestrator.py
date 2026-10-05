from __future__ import annotations

from dataclasses import dataclass

from telepat.llm.router import llm_router
from .context_builder import build_context_packet, classify_intent
from .models import ChatRequest, ChatResponse
from .plan import build_plan
from .session_manager import session_manager


@dataclass(slots=True)
class Orchestrator:
    """Central TELEPAT control plane.

    The orchestrator plans and coordinates. It does not perform astrology,
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

        return ChatResponse(
            reply=reply,
            user_id=session.user_id,
            session_id=session.session_id,
            intent=plan.intent,
            avatar_state=plan.avatar_state,
            provider=provider.name,
        )


orchestrator = Orchestrator()
