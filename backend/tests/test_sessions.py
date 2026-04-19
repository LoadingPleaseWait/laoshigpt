from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_start_session() -> None:
    response = client.post(
        "/v1/sessions/start",
        json={
            "user_id": "user_123",
            "mode": "scenario",
            "scenario": "food_ordering",
            "hsk_level": "HSK1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"].startswith("sess_")
    assert data["mode"] == "scenario"
