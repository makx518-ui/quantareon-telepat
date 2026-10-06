import json

import telepat.config.preflight as preflight_module
from telepat.config.preflight import configuration_preflight


class _Settings:
    def __init__(
        self,
        *,
        env: str = "development",
        provider: str = "auto",
        model: str = "",
        fallbacks=("groq", "gemini", "openai", "claude", "mock"),
        cors=("*",),
        claude_model: str = "",
    ) -> None:
        self.env = env
        self.conversation_provider = provider
        self.conversation_model = model
        self.conversation_fallbacks = tuple(fallbacks)
        self.groq_model = "groq-model"
        self.gemini_model = "gemini-model"
        self.openai_model = "openai-model"
        self.claude_model = claude_model
        self.astro_provider = "gemini"
        self.astro_model = "gemini-astro"
        self.cors_origins = tuple(cors)

    def model_for(self, provider: str, provider_default: str) -> str:
        if (
            self.conversation_provider == provider
            and self.conversation_model
        ):
            return self.conversation_model
        return provider_default


def test_config_preflight_accepts_safe_development_defaults(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "settings",
        _Settings(),
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MEMORY_API_URL", raising=False)
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    report = configuration_preflight()

    assert report["ok"] is True
    assert report["errors"] == []


def test_config_preflight_blocks_wildcard_cors_in_production(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "settings",
        _Settings(env="production", cors=("*",)),
    )
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    report = configuration_preflight()

    assert report["ok"] is False
    assert "production_cors_not_restricted" in report["errors"]


def test_config_preflight_requires_selected_provider_key(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "settings",
        _Settings(provider="openai"),
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    report = configuration_preflight()

    assert "conversation_provider_key_missing" in report["errors"]


def test_config_preflight_detects_incomplete_yandex_iam(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "settings",
        _Settings(),
    )
    monkeypatch.setenv("YANDEX_IAM_TOKEN", "token")
    monkeypatch.delenv("YANDEX_FOLDER_ID", raising=False)
    monkeypatch.delenv("YANDEX_SPEECHKIT_API_KEY", raising=False)
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    report = configuration_preflight()

    assert "yandex_iam_pair_incomplete" in report["errors"]


def test_config_preflight_validates_cost_rates_json(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "settings",
        _Settings(),
    )
    monkeypatch.setenv("TELEPAT_COST_RATES_JSON", "{not-json")
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    report = configuration_preflight()

    assert "cost_rates_invalid" in report["errors"]
    assert report["cost_rates"]["valid"] is False


def test_config_preflight_accepts_cache_write_rate(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "settings",
        _Settings(),
    )
    monkeypatch.setenv(
        "TELEPAT_COST_RATES_JSON",
        json.dumps(
            {
                "claude-model": {
                    "input": 1.0,
                    "cached_input": 0.1,
                    "cache_write": 1.25,
                    "output": 5.0,
                }
            }
        ),
    )
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    report = configuration_preflight()

    assert report["cost_rates"]["valid"] is True
    assert report["cost_rates"]["models"] == 1


def test_config_preflight_requires_engine_when_gpu_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "settings",
        _Settings(),
    )
    monkeypatch.setenv("TELEPAT_AVATAR_GPU_ENABLED", "1")
    monkeypatch.delenv("TELEPAT_AVATAR_ENGINE", raising=False)
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    report = configuration_preflight()

    assert "avatar_gpu_enabled_without_engine" in report["errors"]
