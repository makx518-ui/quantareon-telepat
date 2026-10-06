from fastapi.testclient import TestClient

from telepat.api.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["version"] == "0.4.0"



def test_metrics_health_contains_no_user_content() -> None:
    response = client.get("/health/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["privacy"] == "no_user_content"
    assert isinstance(data["stages"], dict)
