import pytest

from telepat.core.models import ContextPacket
from telepat.llm.router import llm_router


@pytest.mark.asyncio
async def test_auto_router_falls_back_to_mock_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    context = ContextPacket(
        session_id="s",
        user_id="u",
        language="ru",
        current_message="Привет",
        intent="casual_conversation",
    )

    text, provider = await llm_router.generate(context, provider="auto")
    assert text
    assert provider == "mock"
