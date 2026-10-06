from fastapi.testclient import TestClient

from telepat.api.main import app


client = TestClient(app)


def test_provider_health_exposes_only_booleans() -> None:
    response = client.get("/health/providers")
    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(isinstance(value, bool) for value in data.values())
    assert "gemini" in data
    assert "deepgram" in data
    assert "memory" in data


def test_readiness_separates_core_from_external_providers(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_SPEECHKIT_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_IAM_TOKEN", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    response = client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()

    assert data["core_ready"] is True
    assert data["astro_engine_ready"] is True
    assert data["conversation_ready"] is False
    assert data["voice_input_ready"] is False
    assert data["voice_output_ready"] is False
    assert data["live_voice_ready"] is False
    assert data["full_telepat_ready"] is False
    assert isinstance(data["providers"], dict)



def test_provider_contract_lists_missing_variable_names_only(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_SPEECHKIT_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_IAM_TOKEN", raising=False)
    monkeypatch.delenv("YANDEX_FOLDER_ID", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    monkeypatch.delenv("MEMORY_API_URL", raising=False)

    response = client.get("/health/provider-contract")
    assert response.status_code == 200
    data = response.json()

    providers = data["providers"]
    assert providers["gemini"]["missing"] == ["GEMINI_API_KEY"]
    assert providers["deepgram"]["missing"] == ["DEEPGRAM_API_KEY"]
    assert providers["memory"]["missing"] == ["MEMORY_API_URL"]

    yandex = providers["yandex_ermil"]
    assert yandex["ready"] is False
    assert len(yandex["alternatives"]) == 2

    serialized = str(data)
    assert "secret-value" not in serialized



def test_production_readiness_lists_runtime_blockers(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_SPEECHKIT_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_IAM_TOKEN", raising=False)
    monkeypatch.delenv("YANDEX_FOLDER_ID", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    monkeypatch.delenv("MEMORY_API_URL", raising=False)
    monkeypatch.delenv("TELEPAT_AVATAR_ENGINE", raising=False)
    monkeypatch.delenv("TELEPAT_AVATAR_GPU_ENABLED", raising=False)

    response = client.get("/health/production-readiness")
    assert response.status_code == 200
    data = response.json()

    assert data["ready"] is False
    assert "conversation_provider" in data["blockers"]
    assert "astro_interpreter" in data["blockers"]
    assert "voice_input" in data["blockers"]
    assert "voice_output" in data["blockers"]
    assert "memory" in data["blockers"]
    assert "avatar_engine" in data["blockers"]
    assert "avatar_gpu" in data["blockers"]
    assert data["capabilities"]["astrofractal_engine"] is True



def test_memory_readiness_requires_recall_and_store(monkeypatch) -> None:
    import telepat.api.status as status_module

    class _Memory:
        configured = True
        recall_enabled = True
        store_enabled = False

    monkeypatch.setattr(status_module, "memory_adapter", _Memory())

    providers = status_module.provider_status()
    readiness = status_module.readiness_status()
    contract = status_module.provider_contract()

    assert providers["memory"] is True
    assert readiness["memory_ready"] is False
    assert contract["providers"]["memory"]["ready"] is True
    assert contract["providers"]["memory"]["operational"] is False
    assert contract["providers"]["memory"]["controls"] == {
        "recall_enabled": True,
        "store_enabled": False,
    }



def test_production_mode_blocks_wildcard_cors(monkeypatch) -> None:
    import telepat.api.status as status_module

    class _Settings:
        env = "production"
        cors_origins = ("*",)
        claude_model = ""

        @staticmethod
        def model_for(provider: str, provider_default: str) -> str:
            return provider_default

    monkeypatch.setattr(status_module, "settings", _Settings())

    readiness = status_module.production_readiness_status()

    assert "cors_policy" in readiness["blockers"]
    assert readiness["capabilities"]["cors_policy"] is False


def test_development_mode_allows_wildcard_cors(monkeypatch) -> None:
    import telepat.api.status as status_module

    class _Settings:
        env = "development"
        cors_origins = ("*",)
        claude_model = ""

        @staticmethod
        def model_for(provider: str, provider_default: str) -> str:
            return provider_default

    monkeypatch.setattr(status_module, "settings", _Settings())

    readiness = status_module.production_readiness_status()

    assert "cors_policy" not in readiness["blockers"]
    assert readiness["capabilities"]["cors_policy"] is True


def test_missing_cost_rates_is_warning_not_blocker(monkeypatch) -> None:
    import telepat.api.status as status_module

    monkeypatch.setenv("GEMINI_API_KEY", "configured")
    monkeypatch.setenv("TELEPAT_COST_RATES_JSON", "{}")

    class _Settings:
        env = "production"
        cors_origins = ("https://quantareon.example",)
        claude_model = ""

        @staticmethod
        def model_for(provider: str, provider_default: str) -> str:
            return provider_default

    monkeypatch.setattr(status_module, "settings", _Settings())

    readiness = status_module.production_readiness_status()

    assert "llm_cost_rates_unconfigured" in readiness["warnings"]
    assert "llm_cost_rates_unconfigured" not in readiness["blockers"]



def test_shared_session_store_removes_single_container_warning(
    monkeypatch,
) -> None:
    import telepat.api.status as status_module

    class _Settings:
        env = "production"
        cors_origins = ("https://quantareon.example",)
        claude_model = ""

        @staticmethod
        def model_for(provider: str, provider_default: str) -> str:
            return provider_default

    class _SharedStore:
        kind = "shared"
        ttl_seconds = 21600
        max_sessions = 1000
        max_history_turns = 60

    monkeypatch.setattr(status_module, "settings", _Settings())
    monkeypatch.setattr(status_module, "session_store", _SharedStore())

    readiness = status_module.production_readiness_status()

    assert "single_container_session_store" not in readiness["warnings"]
