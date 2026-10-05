from fastapi.testclient import TestClient

from telepat.api.main import app


client = TestClient(app)


def test_session_bootstrap_creates_identity() -> None:
    response = client.post(
        "/session/bootstrap",
        json={"language": "ru"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"]
    assert data["session_id"]
    assert data["language"] == "ru"
    assert data["astro_ready"] is False


def test_session_bootstrap_reuses_session() -> None:
    first = client.post(
        "/session/bootstrap",
        json={"language": "ru"},
    ).json()

    second = client.post(
        "/session/bootstrap",
        json={
            "language": "ru",
            "user_id": first["user_id"],
            "session_id": first["session_id"],
        },
    ).json()

    assert second["user_id"] == first["user_id"]
    assert second["session_id"] == first["session_id"]
