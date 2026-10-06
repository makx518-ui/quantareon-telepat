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
