from fastapi.testclient import TestClient

from telepat import __version__
from telepat.api.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["version"] == __version__
    assert __version__ == "0.5.0"
    assert isinstance(data["build_sha"], str)
    assert data["build_sha"]



def test_metrics_health_contains_no_user_content() -> None:
    response = client.get("/health/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["privacy"] == "no_user_content"
    assert isinstance(data["stages"], dict)



def test_privacy_health_reports_retention_controls() -> None:
    response = client.get("/health/privacy")
    assert response.status_code == 200
    data = response.json()

    assert data["metrics_store_user_content"] is False
    assert data["rate_limit_identity_hashed"] is True
    assert data["session_store"] == "in_process"
    assert data["session_ttl_seconds"] > 0
    assert data["max_sessions"] > 0
    assert data["max_history_turns"] > 0

    usage_retention = data["usage_retention"]
    assert usage_retention["ttl_seconds"] > 0
    assert usage_retention["max_sessions"] > 0
    assert usage_retention["stores_user_content"] is False

    memory = data["memory"]
    assert isinstance(memory["configured"], bool)
    assert isinstance(memory["recall_enabled"], bool)
    assert isinstance(memory["store_enabled"], bool)
    assert isinstance(memory["external_persistence"], bool)
