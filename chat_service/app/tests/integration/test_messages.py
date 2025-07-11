import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_message(client: AsyncClient, auth_header, mock_redis, test_user, test_chat):
    response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello, World!", "chat_id": test_chat.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Hello, World!"
    assert data["chat_id"] == test_chat.id
    assert "id" in data
    assert "created_at" in data
    assert "user" in data
    assert data["is_deleted"] == False
    assert "statuses" in data


async def test_read_messages(client: AsyncClient, auth_header, test_chat):
    # Create multiple messages
    for i in range(5):
        await client.post(
            "/api/v1/messages/",
            headers=auth_header,
            json={"content": f"Message {i}", "chat_id": test_chat.id}
        )

    response = await client.get(f"/api/v1/messages/{test_chat.id}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    for msg in data:
        assert "id" in msg
        assert "content" in msg
        assert "created_at" in msg
        assert "user" in msg
        assert "statuses" in msg


async def test_update_message(client: AsyncClient, auth_header, test_chat):
    # Create a message
    create_response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Original message", "chat_id": test_chat.id}
    )
    message_id = create_response.json()["id"]

    # Update the message
    update_response = await client.put(
        f"/api/v1/messages/{message_id}",
        headers=auth_header,
        json={"content": "Updated message"}
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["content"] == "Updated message"
    assert "updated_at" in updated_data


async def test_delete_message(client: AsyncClient, auth_header, test_chat):
    # Create a message
    create_response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Message to delete", "chat_id": test_chat.id}
    )
    message_id = create_response.json()["id"]

    # Delete the message
    delete_response = await client.delete(f"/api/v1/messages/{message_id}", headers=auth_header)
    assert delete_response.status_code == 204
    
    # Verify deletion by fetching messages and checking the content
    messages_response = await client.get(f"/api/v1/messages/{test_chat.id}", headers=auth_header)
    assert messages_response.status_code == 200
    messages = messages_response.json()
    deleted_message = next((msg for msg in messages if msg["id"] == message_id), None)
    assert deleted_message is not None
    assert deleted_message["is_deleted"] == True
    assert deleted_message["content"] == "<This message has been deleted>"


async def test_update_message_status(client: AsyncClient, auth_header, test_chat):
    # Create a message
    create_response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Message to update status", "chat_id": test_chat.id}
    )
    message_id = create_response.json()["id"]

    # Update message status
    status_response = await client.put(
        f"/api/v1/messages/{message_id}/status",
        headers=auth_header,
        json={"is_read": True}
    )
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert any(status["is_read"] for status in status_data["statuses"])


async def test_get_messages_with_pagination(client: AsyncClient, auth_header, test_chat):
    # Create 20 messages
    for i in range(20):
        await client.post(
            "/api/v1/messages/",
            headers=auth_header,
            json={"content": f"Message {i}", "chat_id": test_chat.id}
        )

    # Get first page
    response1 = await client.get(f"/api/v1/messages/{test_chat.id}?skip=0&limit=10", headers=auth_header)
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1) == 10

    # Get second page
    response2 = await client.get(f"/api/v1/messages/{test_chat.id}?skip=10&limit=10", headers=auth_header)
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 10

    # Ensure no duplicate messages
    ids1 = {msg["id"] for msg in data1}
    ids2 = {msg["id"] for msg in data2}
    assert len(ids1.intersection(ids2)) == 0


async def test_create_message_invalid_chat(client: AsyncClient, auth_header):
    response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello", "chat_id": 99999}
    )
    assert response.status_code == 404


async def test_get_messages_invalid_chat(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/messages/99999", headers=auth_header)
    # Returns empty list for non-existent chat instead of 404
    assert response.status_code == 200
    assert response.json() == []


async def test_update_message_not_found(client: AsyncClient, auth_header):
    response = await client.put(
        "/api/v1/messages/99999",
        headers=auth_header,
        json={"content": "Updated"}
    )
    assert response.status_code == 404


async def test_delete_message_not_found(client: AsyncClient, auth_header):
    response = await client.delete("/api/v1/messages/99999", headers=auth_header)
    assert response.status_code == 404


async def test_update_message_status_not_found(client: AsyncClient, auth_header):
    response = await client.put(
        "/api/v1/messages/99999/status",
        headers=auth_header,
        json={"is_read": True}
    )
    assert response.status_code == 404


async def test_create_message_unauthorized(client: AsyncClient, test_chat):
    response = await client.post(
        "/api/v1/messages/",
        json={"content": "Hello", "chat_id": test_chat.id}
    )
    assert response.status_code == 401


async def test_get_messages_unauthorized(client: AsyncClient, test_chat):
    response = await client.get(f"/api/v1/messages/{test_chat.id}")
    assert response.status_code == 401


async def test_update_message_unauthorized(client: AsyncClient, test_chat):
    response = await client.put(
        "/api/v1/messages/99999",
        json={"content": "Updated"}
    )
    assert response.status_code == 401


async def test_delete_message_unauthorized(client: AsyncClient):
    response = await client.delete("/api/v1/messages/99999")
    assert response.status_code == 401


async def test_update_message_status_unauthorized(client: AsyncClient):
    response = await client.put(
        "/api/v1/messages/99999/status",
        json={"is_read": True}
    )
    assert response.status_code == 401


async def test_get_messages_with_content_filter(client: AsyncClient, auth_header, test_chat):
    # Create messages with different content
    await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello world", "chat_id": test_chat.id}
    )
    await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Goodbye world", "chat_id": test_chat.id}
    )

    # Filter by specific content
    response = await client.get(f"/api/v1/messages/{test_chat.id}?content=Hello", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Hello" in data[0]["content"]


async def test_create_message_empty_content(client: AsyncClient, auth_header, test_chat):
    response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "", "chat_id": test_chat.id}
    )
    # Application allows empty messages
    assert response.status_code == 200


async def test_update_message_same_user_only(client: AsyncClient, auth_header, test_chat, test_user2):
    # Create message with first user
    create_response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Original message", "chat_id": test_chat.id}
    )
    message_id = create_response.json()["id"]

    # Login as second user
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user2.username, "password": "testpassword2"}
    )
    user2_auth_header = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # Try to update message as different user
    response = await client.put(
        f"/api/v1/messages/{message_id}",
        headers=user2_auth_header,
        json={"content": "Updated by different user"}
    )
    assert response.status_code == 404


async def test_delete_message_same_user_only(client: AsyncClient, auth_header, test_chat, test_user2):
    # Create message with first user
    create_response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Message to delete", "chat_id": test_chat.id}
    )
    message_id = create_response.json()["id"]

    # Login as second user
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user2.username, "password": "testpassword2"}
    )
    user2_auth_header = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # Try to delete message as different user
    response = await client.delete(f"/api/v1/messages/{message_id}", headers=user2_auth_header)
    assert response.status_code == 404
