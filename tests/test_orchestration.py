import pytest

from telepat.core.models import ChatRequest
from telepat.core.orchestrator import orchestrator
from telepat.core.plan import build_plan
from telepat.core.session_manager import session_manager
from telepat.llm.router import ConversationUnavailableError, llm_router


def test_astro_plan_uses_astro_and_memory() -> None:
    plan = build_plan("astropsychology")
    assert plan.use_astro is True
    assert plan.use_memory is True
    assert plan.psychology_level == "full"
    assert plan.avatar_state == "thinking"


def test_casual_plan_avoids_unnecessary_astro() -> None:
    plan = build_plan("casual_conversation")
    assert plan.use_astro is False
    assert plan.psychology_level == "light"
    assert plan.avatar_state == "idle"


def test_explicit_memory_plan_is_deep_memory_without_astro() -> None:
    plan = build_plan("factual_user_memory")
    assert plan.use_memory is True
    assert plan.use_astro is False
    assert plan.response_mode == "memory"



@pytest.mark.asyncio
async def test_failed_llm_turn_is_not_committed_to_session(monkeypatch) -> None:
    async def unavailable(*args, **kwargs):
        raise ConversationUnavailableError("provider outage")

    monkeypatch.setattr(llm_router, "generate", unavailable)

    request = ChatRequest(
        message="Повтори после сбоя",
        user_id="orchestrator-failure-user",
        session_id="orchestrator-failure-session",
        language="ru",
    )

    with pytest.raises(ConversationUnavailableError):
        await orchestrator.handle_chat(request)

    session = session_manager.get("orchestrator-failure-session")
    assert session is not None
    assert session.history == []
