from telepat.config.settings import Settings, _origins


def test_generic_model_override_applies_only_to_selected_provider() -> None:
    cfg = Settings(
        conversation_provider="openai",
        conversation_model="gpt-custom",
        gemini_model="gemini-default",
        groq_model="groq-default",
        openai_model="gpt-default",
        claude_model="claude-default",
    )

    assert cfg.model_for("openai", cfg.openai_model) == "gpt-custom"
    assert cfg.model_for("gemini", cfg.gemini_model) == "gemini-default"
    assert cfg.model_for("groq", cfg.groq_model) == "groq-default"
    assert cfg.model_for("claude", cfg.claude_model) == "claude-default"


def test_auto_mode_never_leaks_generic_model_between_providers() -> None:
    cfg = Settings(
        conversation_provider="auto",
        conversation_model="should-not-leak",
        gemini_model="gemini-default",
        groq_model="groq-default",
        openai_model="gpt-default",
        claude_model="claude-default",
    )

    assert cfg.model_for("gemini", cfg.gemini_model) == "gemini-default"
    assert cfg.model_for("groq", cfg.groq_model) == "groq-default"
    assert cfg.model_for("openai", cfg.openai_model) == "gpt-default"
    assert cfg.model_for("claude", cfg.claude_model) == "claude-default"



def test_cors_origin_parser_preserves_urls(monkeypatch) -> None:
    monkeypatch.setenv(
        "TEST_CORS",
        "https://quantareon.com/, https://preview.example",
    )

    assert _origins("TEST_CORS", "*") == (
        "https://quantareon.com",
        "https://preview.example",
    )
