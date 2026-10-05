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
