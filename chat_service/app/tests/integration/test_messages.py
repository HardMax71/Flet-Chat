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
    assert delete_response.status_code == 200
    deleted_data = delete_response.json()
    assert deleted_data["is_deleted"] == True
    assert deleted_data["content"] == "<This message has been deleted>"


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
