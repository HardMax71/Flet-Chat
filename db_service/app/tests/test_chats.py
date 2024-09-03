# app/tests/test_chats.py
def test_create_chat(client, auth_header, test_user2, db_session):
    response = client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user2.id]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Chat"
    assert len(data["members"]) == 2


def test_get_chats(client, auth_header, db_session):
    # Create a chat first
    client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )

    response = client.get("/api/v1/chats/", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_start_chat(client, auth_header, test_user2):
    response = client.post(
        f"/api/v1/chats/start?other_user_id={test_user2.id}",
        headers=auth_header
    )
    assert response.status_code == 200
    data = response.json()
    assert f"Chat with {test_user2.username}" in data["name"]



def test_add_chat_member(client, auth_header, test_user, test_user2, db_session):
    # Create a chat first
    chat_response = client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    assert chat_response.status_code == 200, f"Failed to create chat: {chat_response.text}"
    chat_id = chat_response.json()["id"]

    response = client.post(
        f"/api/v1/chats/{chat_id}/members",
        headers=auth_header,
        json={"user_id": test_user2.id}
    )
    assert response.status_code == 200, f"Failed to add member: {response.text}"
    data = response.json()
    assert len(data["members"]) == 2, f"Expected 2 members, got {len(data['members'])}"
    member_ids = [member["id"] for member in data["members"]]
    assert test_user.id in member_ids, f"test_user not in members: {member_ids}"
    assert test_user2.id in member_ids, f"test_user2 not in members: {member_ids}"
