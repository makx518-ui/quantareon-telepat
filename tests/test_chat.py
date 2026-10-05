from fastapi.testclient import TestClient

from telepat.api.main import app


client = TestClient(app)


def test_chat_creates_session() -> None:
    response = client.post(
        "/chat",
        json={"message": "Привет", "language": "ru"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reply"]
    assert data["session_id"]
    assert data["user_id"]
    assert data["provider"] == "mock"


def test_chat_reuses_session() -> None:
    first = client.post("/chat", json={"message": "Привет", "language": "ru"}).json()
    second = client.post(
        "/chat",
        json={
            "message": "Мне тревожно, что делать?",
            "language": "ru",
            "session_id": first["session_id"],
            "user_id": first["user_id"],
        },
    ).json()
    assert second["session_id"] == first["session_id"]
    assert second["user_id"] == first["user_id"]
    assert second["intent"] == "personal_reflection"
