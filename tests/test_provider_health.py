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
