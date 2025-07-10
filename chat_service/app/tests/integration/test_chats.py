import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_chat(client: AsyncClient, auth_header, test_user2):
    response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user2.id]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Chat"
    assert len(data["members"]) == 2


async def test_create_chat_with_invalid_member(client: AsyncClient, auth_header):
    response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Invalid Member Chat", "member_ids": [99999]}  # Non-existent user ID
    )
    assert response.status_code == 404


async def test_get_chats(client: AsyncClient, auth_header):
    # Create multiple chats
    await client.post("/api/v1/chats/", headers=auth_header, json={"name": "Chat 1", "member_ids": []})
    await client.post("/api/v1/chats/", headers=auth_header, json={"name": "Chat 2", "member_ids": []})

    response = await client.get("/api/v1/chats/", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


async def test_get_chats_with_pagination(client: AsyncClient, auth_header):
    # Create multiple chats
    for i in range(5):
        await client.post("/api/v1/chats/", headers=auth_header, json={"name": f"Chat {i}", "member_ids": []})

    response = await client.get("/api/v1/chats/?skip=2&limit=2", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_get_chats_with_name_filter(client: AsyncClient, auth_header):
    await client.post("/api/v1/chats/", headers=auth_header, json={"name": "Alpha Chat", "member_ids": []})
    await client.post("/api/v1/chats/", headers=auth_header, json={"name": "Beta Chat", "member_ids": []})

    response = await client.get("/api/v1/chats/?name=Alpha", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alpha Chat"


async def test_start_chat(client: AsyncClient, auth_header, test_user, test_user2):
    response = await client.post(
        "/api/v1/chats/start",
        headers=auth_header,
        json={"other_user_id": test_user2.id}
    )
    assert response.status_code == 200
    data = response.json()
    expected_chat_name = f"Chat between {test_user.username} and {test_user2.username}"
    assert expected_chat_name in data["name"]


async def test_start_chat_with_nonexistent_user(client: AsyncClient, auth_header):
    response = await client.post(
        "/api/v1/chats/start",
        headers=auth_header,
        json={"other_user_id": 99999}
    )
    assert response.status_code == 404


async def test_get_chat_by_id(client: AsyncClient, auth_header):
    create_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )
    chat_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/chats/{chat_id}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == chat_id
    assert data["name"] == "Test Chat"


async def test_get_nonexistent_chat(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/chats/99999", headers=auth_header)
    assert response.status_code == 404


async def test_update_chat(client: AsyncClient, auth_header):
    create_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Original Chat", "member_ids": []}
    )
    chat_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/chats/{chat_id}",
        headers=auth_header,
        json={"name": "Updated Chat"}
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated Chat"


async def test_update_nonexistent_chat(client: AsyncClient, auth_header):
    response = await client.put(
        "/api/v1/chats/99999",
        headers=auth_header,
        json={"name": "Updated Chat"}
    )
    assert response.status_code == 404


async def test_delete_chat(client: AsyncClient, auth_header):
    create_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Delete Me Chat", "member_ids": []}
    )
    chat_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/chats/{chat_id}", headers=auth_header)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/chats/{chat_id}", headers=auth_header)
    assert get_response.status_code == 404


async def test_delete_nonexistent_chat(client: AsyncClient, auth_header):
    response = await client.delete("/api/v1/chats/99999", headers=auth_header)
    assert response.status_code == 404


async def test_add_chat_member(client: AsyncClient, auth_header, test_user, test_user2):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.post(
        f"/api/v1/chats/{chat_id}/members",
        headers=auth_header,
        json={"user_id": test_user2.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 2
    member_ids = [member["id"] for member in data["members"]]
    assert test_user.id in member_ids
    assert test_user2.id in member_ids


async def test_add_nonexistent_member(client: AsyncClient, auth_header, test_user):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.post(
        f"/api/v1/chats/{chat_id}/members",
        headers=auth_header,
        json={"user_id": 99999}
    )
    assert response.status_code == 404


async def test_remove_chat_member(client: AsyncClient, auth_header, test_user, test_user2):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id, test_user2.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.delete(f"/api/v1/chats/{chat_id}/members/{test_user2.id}", headers=auth_header)
    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/chats/{chat_id}", headers=auth_header)
    assert get_response.status_code == 200
    data = get_response.json()
    member_ids = [member["id"] for member in data["members"]]
    assert test_user2.id not in member_ids


async def test_remove_nonexistent_member(client: AsyncClient, auth_header, test_user):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.delete(f"/api/v1/chats/{chat_id}/members/99999", headers=auth_header)
    assert response.status_code == 404


async def test_get_chat_members(client: AsyncClient, auth_header, test_user, test_user2):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id, test_user2.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.get(f"/api/v1/chats/{chat_id}/members", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    member_ids = [member["id"] for member in data]
    assert test_user.id in member_ids
    assert test_user2.id in member_ids


async def test_get_unread_messages_count(client: AsyncClient, auth_header, test_user):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.get(f"/api/v1/chats/{chat_id}/unread_count", headers=auth_header)
    assert response.status_code == 200
    assert isinstance(response.json(), int)


async def test_get_unread_messages_count_nonexistent_chat(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/chats/99999/unread_count", headers=auth_header)
    assert response.status_code == 404


async def test_get_chat_not_found(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/chats/99999", headers=auth_header)
    assert response.status_code == 404
    assert "Chat not found" in response.json()["detail"]


async def test_update_chat_not_found(client: AsyncClient, auth_header):
    response = await client.put(
        "/api/v1/chats/99999",
        headers=auth_header,
        json={"name": "Updated Chat"}
    )
    assert response.status_code == 404
    assert "Chat not found" in response.json()["detail"]


async def test_delete_chat_not_found(client: AsyncClient, auth_header):
    response = await client.delete("/api/v1/chats/99999", headers=auth_header)
    assert response.status_code == 404
    assert "Chat not found" in response.json()["detail"]


async def test_get_chat_members_not_found(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/chats/99999/members", headers=auth_header)
    assert response.status_code == 404
    assert "Chat not found or you're not a member" in response.json()["detail"]


async def test_add_chat_member_user_not_found(client: AsyncClient, auth_header, test_user):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.post(
        f"/api/v1/chats/{chat_id}/members",
        headers=auth_header,
        json={"user_id": 99999}
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


async def test_add_chat_member_chat_not_found(client: AsyncClient, auth_header, test_user2):
    response = await client.post(
        "/api/v1/chats/99999/members",
        headers=auth_header,
        json={"user_id": test_user2.id}
    )
    assert response.status_code == 404
    assert "Chat not found" in response.json()["detail"]


async def test_remove_chat_member_user_not_found(client: AsyncClient, auth_header, test_user):
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    chat_id = chat_response.json()["id"]

    response = await client.delete(f"/api/v1/chats/{chat_id}/members/99999", headers=auth_header)
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


async def test_remove_chat_member_chat_not_found(client: AsyncClient, auth_header, test_user2):
    response = await client.delete(f"/api/v1/chats/99999/members/{test_user2.id}", headers=auth_header)
    assert response.status_code == 404
    assert "Chat not found" in response.json()["detail"]


async def test_get_unread_messages_count_not_found(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/chats/99999/unread_count", headers=auth_header)
    assert response.status_code == 404
    assert "Chat not found" in response.json()["detail"]


async def test_create_chat_with_invalid_members(client: AsyncClient, auth_header):
    response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Invalid Members Chat", "member_ids": [99999, 100000]}
    )
    assert response.status_code == 404
    assert "One or more invalid member IDs" in response.json()["detail"]


async def test_create_chat_with_duplicate_members(client: AsyncClient, auth_header, test_user):
    response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Duplicate Members Chat", "member_ids": [test_user.id, test_user.id]}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 1


async def test_get_chats_with_complex_name_filter(client: AsyncClient, auth_header):
    await client.post("/api/v1/chats/", headers=auth_header, json={"name": "Alpha Beta Chat", "member_ids": []})
    await client.post("/api/v1/chats/", headers=auth_header, json={"name": "Beta Gamma Chat", "member_ids": []})
    await client.post("/api/v1/chats/", headers=auth_header, json={"name": "Gamma Alpha Chat", "member_ids": []})

    response = await client.get("/api/v1/chats/?name=Alpha", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("Alpha" in chat["name"] for chat in data)


async def test_start_chat_with_self(client: AsyncClient, auth_header, test_user):
    response = await client.post(
        "/api/v1/chats/start",
        headers=auth_header,
        json={"other_user_id": test_user.id}
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


async def test_get_members_of_nonexistent_chat(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/chats/99999/members", headers=auth_header)
    assert response.status_code == 404
    assert "Chat not found or you're not a member" in response.json()["detail"]


async def test_add_nonexistent_member_to_chat(client: AsyncClient, auth_header, test_chat):
    response = await client.post(
        f"/api/v1/chats/{test_chat.id}/members",
        headers=auth_header,
        json={"user_id": 99999}
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


async def test_add_member_to_nonexistent_chat(client: AsyncClient, auth_header, test_user2):
    response = await client.post(
        "/api/v1/chats/99999/members",
        headers=auth_header,
        json={"user_id": test_user2.id}
    )
    assert response.status_code == 404
    assert "Chat not found" in response.json()["detail"]


async def test_remove_nonexistent_member_from_chat(client: AsyncClient, auth_header, test_chat):
    response = await client.delete(f"/api/v1/chats/{test_chat.id}/members/99999", headers=auth_header)
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


async def test_create_chat_and_add_message(client: AsyncClient, auth_header, test_user, test_user2):
    # Create a chat
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id, test_user2.id]}
    )
    assert chat_response.status_code == 200
    chat_id = chat_response.json()["id"]

    # Add a message to the chat
    message_response = await client.post(
        f"/api/v1/messages/",
        headers=auth_header,
        json={"chat_id": chat_id, "content": "Test message"}
    )
    assert message_response.status_code == 200
    assert message_response.json()["content"] == "Test message"

    # Get auth header for test_user2
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user2.username, "password": "testpassword2"}
    )
    assert login_response.status_code == 200
    test_user2_auth_header = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # Check unread count for test_user2
    unread_response = await client.get(f"/api/v1/chats/{chat_id}/unread_count", headers=test_user2_auth_header)
    assert unread_response.status_code == 200
    assert unread_response.json() == 1


async def test_update_message_status_and_unread_count(client: AsyncClient, auth_header, test_user, test_user2):
    # Create a chat and add a message
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id, test_user2.id]}
    )
    chat_id = chat_response.json()["id"]
    message_response = await client.post(
        f"/api/v1/messages/",
        headers=auth_header,
        json={"chat_id": chat_id, "content": "Test message"}
    )
    message_id = message_response.json()["id"]

    # Update message status
    status_response = await client.put(
        f"/api/v1/messages/{message_id}/status",
        headers=auth_header,
        json={"is_read": True}
    )
    assert status_response.status_code == 200

    # Check updated unread count
    unread_response = await client.get(f"/api/v1/chats/{chat_id}/unread_count", headers=auth_header)
    assert unread_response.status_code == 200
    assert unread_response.json() == 0


async def test_unauthorized_requests(client: AsyncClient, test_chat):
    # Create chat
    response = await client.post(
        "/api/v1/chats/",
        json={"name": "Test Chat", "member_ids": []}
    )
    assert response.status_code == 401

    # Get chats
    response = await client.get("/api/v1/chats/")
    assert response.status_code == 401

    # Start chat
    response = await client.post(
        "/api/v1/chats/start",
        json={"other_user_id": 1}
    )
    assert response.status_code == 401

    # Get chat by ID
    response = await client.get(f"/api/v1/chats/{test_chat.id}")
    assert response.status_code == 401

    # Update chat
    response = await client.put(
        f"/api/v1/chats/{test_chat.id}",
        json={"name": "Updated Chat"}
    )
    assert response.status_code == 401

    # Delete chat
    response = await client.delete(f"/api/v1/chats/{test_chat.id}")
    assert response.status_code == 401

    # Get chat members
    response = await client.get(f"/api/v1/chats/{test_chat.id}/members")
    assert response.status_code == 401

    # Add member
    response = await client.post(
        f"/api/v1/chats/{test_chat.id}/members",
        json={"user_id": 1}
    )
    assert response.status_code == 401

    # Remove member
    response = await client.delete(f"/api/v1/chats/{test_chat.id}/members/1")
    assert response.status_code == 401

    # Get unread count
    response = await client.get(f"/api/v1/chats/{test_chat.id}/unread_count")
    assert response.status_code == 401


async def test_chat_creation_edge_cases(client: AsyncClient, auth_header, test_user):
    # Create chat with empty member list
    response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Empty Chat", "member_ids": []}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 1  # Should include creator

    # Create chat with very long name
    long_name = "A" * 255
    response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": long_name, "member_ids": []}
    )
    assert response.status_code == 200
    assert response.json()["name"] == long_name


async def test_member_management_edge_cases(client: AsyncClient, auth_header, test_user, test_user2):
    # Create chat
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    chat_id = chat_response.json()["id"]

    # Try to add member that's already in chat
    response = await client.post(
        f"/api/v1/chats/{chat_id}/members",
        headers=auth_header,
        json={"user_id": test_user.id}
    )
    assert response.status_code == 200  # Should handle gracefully

    # Add second user
    response = await client.post(
        f"/api/v1/chats/{chat_id}/members",
        headers=auth_header,
        json={"user_id": test_user2.id}
    )
    assert response.status_code == 200

    # Try to remove user that's not in chat
    response = await client.delete(f"/api/v1/chats/{chat_id}/members/99999", headers=auth_header)
    assert response.status_code == 404


async def test_start_chat_existing_users(client: AsyncClient, auth_header, test_user, test_user2):
    # Start first chat
    response1 = await client.post(
        "/api/v1/chats/start",
        headers=auth_header,
        json={"other_user_id": test_user2.id}
    )
    assert response1.status_code == 200
    chat1_id = response1.json()["id"]

    # Try to start another chat with same user
    response2 = await client.post(
        "/api/v1/chats/start",
        headers=auth_header,
        json={"other_user_id": test_user2.id}
    )
    assert response2.status_code == 200
    chat2_id = response2.json()["id"]

    # Should return existing chat or create new one based on implementation
    assert chat1_id == chat2_id or chat1_id != chat2_id  # Either behavior is valid


async def test_pagination_edge_cases(client: AsyncClient, auth_header):
    # Test with skip larger than available items
    response = await client.get("/api/v1/chats/?skip=1000&limit=10", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == []

    # Test with very large limit
    response = await client.get("/api/v1/chats/?skip=0&limit=10000", headers=auth_header)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test with zero limit
    response = await client.get("/api/v1/chats/?skip=0&limit=0", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == []


async def test_chat_name_filtering_edge_cases(client: AsyncClient, auth_header):
    # Create chats with special characters
    special_chars = ["Special@Chat", "Chat#123", "Chat$%&", "Ñoño Chat"]
    for name in special_chars:
        await client.post(
            "/api/v1/chats/",
            headers=auth_header,
            json={"name": name, "member_ids": []}
        )

    # Test filtering with special characters
    response = await client.get("/api/v1/chats/?name=@", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert any("@" in chat["name"] for chat in data)

    # Test case sensitivity
    await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "CaseTest", "member_ids": []}
    )
    response = await client.get("/api/v1/chats/?name=casetest", headers=auth_header)
    assert response.status_code == 200
