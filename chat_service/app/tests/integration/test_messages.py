import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_message(client: AsyncClient, auth_header, mock_redis):
    # Create a chat first
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )
    chat_id = chat_response.json()["id"]

    response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello, World!", "chat_id": chat_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Hello, World!"
    assert data["chat_id"] == chat_id
    assert "id" in data
    assert "created_at" in data
    assert "user" in data
    assert data["is_deleted"] == False


async def test_create_message_invalid_chat(client: AsyncClient, auth_header):
    response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello, World!", "chat_id": 99999}  # Non-existent chat
    )
    assert response.status_code == 404


async def test_get_messages(client: AsyncClient, auth_header, mock_redis):
    # Create a chat and multiple messages first
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )
    chat_id = chat_response.json()["id"]

    for i in range(5):
        await client.post(
            "/api/v1/messages/",
            headers=auth_header,
            json={"content": f"Message {i}", "chat_id": chat_id}
        )

    response = await client.get(f"/api/v1/messages/{chat_id}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    for msg in data:
        assert "id" in msg
        assert "content" in msg
        assert "created_at" in msg
        assert "user" in msg


async def test_get_messages_with_content_filter(client: AsyncClient, auth_header, mock_redis):
    # Create a chat and multiple messages first
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )
    chat_id = chat_response.json()["id"]

    await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello, World!", "chat_id": chat_id}
    )
    await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Goodbye, World!", "chat_id": chat_id}
    )

    response = await client.get(f"/api/v1/messages/{chat_id}?content=Hello", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello, World!"


async def test_update_message(client: AsyncClient, auth_header):
    # Create a chat and a message first
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )
    chat_id = chat_response.json()["id"]

    message_response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello, World!", "chat_id": chat_id}
    )
    message_id = message_response.json()["id"]

    response = await client.put(
        f"/api/v1/messages/{message_id}",
        headers=auth_header,
        json={"content": "Updated message"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Updated message"
    assert "updated_at" in data


async def test_update_nonexistent_message(client: AsyncClient, auth_header):
    response = await client.put(
        f"/api/v1/messages/99999",
        headers=auth_header,
        json={"content": "Updated message"}
    )
    assert response.status_code == 404


async def test_delete_message(client: AsyncClient, auth_header, mock_redis):
    # Create a chat and a message first
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )
    chat_id = chat_response.json()["id"]

    message_response = await client.post(
        "/api/v1/messages/",
        headers=auth_header,
        json={"content": "Hello, World!", "chat_id": chat_id}
    )
    message_id = message_response.json()["id"]

    response = await client.delete(f"/api/v1/messages/{message_id}", headers=auth_header)
    assert response.status_code == 200

    # Try to get the deleted message
    response = await client.get(f"/api/v1/messages/{chat_id}", headers=auth_header)
    messages = response.json()
    deleted_message = next((msg for msg in messages if msg["id"] == message_id), None)
    assert deleted_message is not None
    assert deleted_message["content"] == "<This message has been deleted>"
    assert deleted_message["is_deleted"] == True


async def test_delete_nonexistent_message(client: AsyncClient, auth_header):
    response = await client.delete(f"/api/v1/messages/99999", headers=auth_header)
    assert response.status_code == 404


async def test_get_messages_pagination(client: AsyncClient, auth_header, mock_redis):
    # Create a chat and multiple messages first
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )
    chat_id = chat_response.json()["id"]

    for i in range(20):
        await client.post(
            "/api/v1/messages/",
            headers=auth_header,
            json={"content": f"Message {i}", "chat_id": chat_id}
        )

    # Test first page
    response = await client.get(f"/api/v1/messages/{chat_id}?skip=0&limit=10", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10

    # Test second page
    response = await client.get(f"/api/v1/messages/{chat_id}?skip=10&limit=10", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10

    # Test with a larger limit
    response = await client.get(f"/api/v1/messages/{chat_id}?skip=0&limit=30", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 20  # Should return all 20 messages
