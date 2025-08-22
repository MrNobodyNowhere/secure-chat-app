from fastapi.testclient import TestClient
from server.main import app


client = TestClient(app)


def register(username: str, password: str):
    return client.post("/auth/register", json={"username": username, "password": password})


def login(username: str, password: str) -> str:
    res = client.post("/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_auth_and_message_flow():
    # Register users (idempotent-ish)
    register("alice_test", "password123")
    register("bob_test", "password123")

    alice_token = login("alice_test", "password123")
    bob_token = login("bob_test", "password123")

    # Who am I
    me = client.get("/users/me", headers={"Authorization": f"Bearer {alice_token}"})
    assert me.status_code == 200
    alice_id = me.json()["id"]

    users = client.get("/users")
    assert users.status_code == 200
    data = users.json()
    assert any(u["username"] == "alice_test" for u in data)
    bob_id = next(u["id"] for u in data if u["username"] == "bob_test")

    # Send message
    res = client.post(
        "/messages",
        json={"recipient_id": bob_id, "content": "hello there"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res.status_code == 200
    msg = res.json()
    assert msg["content"] == "hello there"
    assert msg["sender_id"] == alice_id
    assert msg["recipient_id"] == bob_id

    # Chat history for bob
    hist = client.get(f"/messages/{alice_id}", headers={"Authorization": f"Bearer {bob_token}"})
    assert hist.status_code == 200
    assert any(m["content"] == "hello there" for m in hist.json()["messages"])

