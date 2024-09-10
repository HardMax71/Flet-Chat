import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_create_message(client: AsyncClient, auth_header):
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

async def test_get_messages(client: AsyncClient, auth_header):
    # Create a chat and a message first
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

    response = await client.get(f"/api/v1/messages/{chat_id}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

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

async def test_delete_message(client: AsyncClient, auth_header):
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
    assert response.status_code == 204

    # Try to get the deleted message
    response = await client.get(f"/api/v1/messages/{chat_id}", headers=auth_header)
    messages = response.json()
    deleted_message = next((msg for msg in messages if msg["id"] == message_id), None)
    assert deleted_message is not None
    assert deleted_message["content"] == "<This message has been deleted>"
    assert deleted_message["is_deleted"] == True