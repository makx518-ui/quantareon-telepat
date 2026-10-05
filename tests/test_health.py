from fastapi.testclient import TestClient

from telepat.api.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["version"] == "0.4.0"
