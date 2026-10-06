from deploy.sync_modal_provider_secret import (
    collect_provider_values,
)


def test_provider_secret_sync_collects_only_non_empty_values(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "  deepgram-test  ")
    monkeypatch.setenv("GROQ_API_KEY", "   ")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    values = collect_provider_values()

    assert values["GEMINI_API_KEY"] == "gemini-test"
    assert values["DEEPGRAM_API_KEY"] == "deepgram-test"
    assert "GROQ_API_KEY" not in values
    assert "OPENAI_API_KEY" not in values
    assert values["TELEPAT_PROVIDER_SECRET_MANAGED"] == "1"



def test_provider_secret_sync_collects_runtime_policy(monkeypatch) -> None:
    monkeypatch.setenv(
        "TELEPAT_CORS_ORIGINS",
        "https://quantareon.example",
    )
    monkeypatch.setenv("TELEPAT_CHAT_RPM", "42")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")
    monkeypatch.setenv(
        "TELEPAT_CONVERSATION_FALLBACKS",
        "gemini,groq,openai",
    )
    monkeypatch.setenv("TELEPAT_ASTRO_PROVIDER", "gemini")
    monkeypatch.setenv(
        "TELEPAT_COST_RATES_JSON",
        '{"gpt-6-luna":{"input":0.05,"output":0.25}}',
    )
    monkeypatch.setenv("YANDEX_TTS_SPEED", "0.96")

    values = collect_provider_values()

    assert values["TELEPAT_CORS_ORIGINS"] == (
        "https://quantareon.example"
    )
    assert values["TELEPAT_CHAT_RPM"] == "42"
    assert values["TELEPAT_MEMORY_STORE_ENABLED"] == "0"
    assert values["TELEPAT_CONVERSATION_FALLBACKS"] == (
        "gemini,groq,openai"
    )
    assert values["TELEPAT_ASTRO_PROVIDER"] == "gemini"
    assert values["TELEPAT_COST_RATES_JSON"].startswith("{")
    assert values["YANDEX_TTS_SPEED"] == "0.96"
