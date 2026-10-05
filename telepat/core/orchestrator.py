from __future__ import annotations

from dataclasses import dataclass

from telepat.llm.router import llm_router
from .context_builder import build_context_packet
from .models import ChatRequest, ChatResponse
from .session_manager import session_manager


@dataclass(slots=True)
class Orchestrator:
    """Central TELEPAT control plane.

    It coordinates modules but does not implement astrology, memory storage,
    TTS, STT or avatar generation itself.
    """

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        session = session_manager.get_or_create(
            session_id=request.session_id,
            user_id=request.user_id,
            language=request.language,
        )

        session_manager.append(session.session_id, "user", request.message)
        context = build_context_packet(session, request.message)

        provider = llm_router.get()
        reply = await provider.generate(context)

        session_manager.append(session.session_id, "assistant", reply)

        avatar_state = self._select_avatar_state(context.intent)
        return ChatResponse(
            reply=reply,
            user_id=session.user_id,
            session_id=session.session_id,
            intent=context.intent,
            avatar_state=avatar_state,
            provider=provider.name,
        )

    @staticmethod
    def _select_avatar_state(intent: str) -> str:
        if intent in {"personal_reflection", "factual_user_memory"}:
            return "listening"
        if intent in {"astropsychology", "follow_up_astro"}:
            return "thinking"
        return "idle"


orchestrator = Orchestrator()
