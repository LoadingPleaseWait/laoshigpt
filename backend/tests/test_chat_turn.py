from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_turn_shape() -> None:
    response = client.post(
        "/v1/chat/turn",
        json={
            "session_id": "sess_abc",
            "user_id": "user_123",
            "user_text": "你好",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "assistant_reply_zh" in data
    assert "corrections" in data
    assert "session_state" in data
