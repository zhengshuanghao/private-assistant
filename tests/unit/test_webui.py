from fastapi.testclient import TestClient

from private_assistent.api.app import app


def test_index_serves_webui():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Private Assistent" in response.text
    assert "模型选择" in response.text
    assert "当前会话" in response.text


def test_chat_api_returns_reply():
    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "hello web"})
    assert response.status_code == 200
    assert "hello web" in response.json()["reply"]



def test_chat_api_persists_session_messages():
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"message": "hello session", "session_id": "test-session"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session"
    assert data["context_messages"] >= 1

    messages = client.get("/api/sessions/test-session/messages")
    assert messages.status_code == 200
    payload = messages.json()
    assert [item["role"] for item in payload] == ["user", "assistant"]
    assert payload[0]["content"] == "hello session"
