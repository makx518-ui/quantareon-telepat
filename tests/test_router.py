import pytest

from telepat.core.models import ContextPacket
from telepat.llm.base import (
    ConversationProvider,
    ConversationResult,
    ProviderUsage,
)
from telepat.llm.router import (
    ConversationUnavailableError,
    LLMRouter,
    llm_router,
)
from telepat.observability.usage import usage_registry


@pytest.mark.asyncio
async def test_auto_router_falls_back_to_mock_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

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


def test_router_registers_all_conversation_candidates() -> None:
    assert llm_router.get("groq") is not None
    assert llm_router.get("gemini") is not None
    assert llm_router.get("openai") is not None
    assert llm_router.get("claude") is not None
    assert llm_router.get("mock") is not None



class _BrokenProvider(ConversationProvider):
    name = "broken"

    @property
    def configured(self) -> bool:
        return True

    async def generate(self, context: ContextPacket) -> str:
        raise RuntimeError("provider outage")


@pytest.mark.asyncio
async def test_real_provider_failure_does_not_fall_back_to_mock(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    router = LLMRouter()
    router.register(_BrokenProvider())

    context = ContextPacket(
        session_id="s",
        user_id="u",
        language="ru",
        current_message="Привет",
        intent="casual_conversation",
    )

    with pytest.raises(
        ConversationUnavailableError,
        match="broken:RuntimeError",
    ):
        await router.generate(context, provider="broken")


@pytest.mark.asyncio
async def test_explicit_mock_remains_available_for_diagnostics() -> None:
    router = LLMRouter()
    router.register(_BrokenProvider())

    context = ContextPacket(
        session_id="s",
        user_id="u",
        language="ru",
        current_message="Привет",
        intent="casual_conversation",
    )

    text, provider = await router.generate(context, provider="mock")

    assert text
    assert provider == "mock"



class _UsageProvider(ConversationProvider):
    name = "usage-provider"

    @property
    def configured(self) -> bool:
        return True

    async def generate(
        self,
        context: ContextPacket,
    ) -> ConversationResult:
        return ConversationResult(
            text="usage reply",
            model="usage-model",
            usage=ProviderUsage(
                input_tokens=120,
                output_tokens=30,
                cached_input_tokens=20,
            ),
        )


@pytest.mark.asyncio
async def test_router_records_provider_usage_per_session() -> None:
    usage_registry.reset()
    router = LLMRouter()
    router.register(_UsageProvider())

    context = ContextPacket(
        session_id="usage-router-session",
        user_id="usage-router-user",
        language="ru",
        current_message="Привет",
        intent="casual_conversation",
    )

    text, provider = await router.generate(
        context,
        provider="usage-provider",
    )

    assert text == "usage reply"
    assert provider == "usage-provider"

    usage = usage_registry.snapshot("usage-router-session")
    assert usage is not None
    assert usage["input_tokens"] == 120
    assert usage["output_tokens"] == 30
    assert usage["cached_input_tokens"] == 20
    assert usage["models"] == {"usage-model": 1}
