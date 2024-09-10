import random

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

async def test_get_chats(client: AsyncClient, auth_header):
    # Create a chat first
    await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": []}
    )

    response = await client.get("/api/v1/chats/", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

async def test_start_chat(client: AsyncClient, auth_header, test_user2):
    response = await client.post(
        f"/api/v1/chats/start",
        headers=auth_header,
        json={"other_user_id": test_user2.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert f"Chat with {test_user2.username}" in data["name"]

async def test_add_chat_member(client: AsyncClient, auth_header, test_user, test_user2):
    # Create a chat first with both users
    chat_response = await client.post(
        "/api/v1/chats/",
        headers=auth_header,
        json={"name": "Test Chat", "member_ids": [test_user.id]}
    )
    assert chat_response.status_code == 200, f"Failed to create chat: {chat_response.text}"
    chat_id = chat_response.json()["id"]

    # Create a third user to add to the chat
    test_user3_response = await client.post(
        "/api/v1/auth/register",
        json={"username": f"testuser3_{random.randint(1000, 9999)}",
              "email": f"testuser3_{random.randint(1000, 9999)}@example.com",
              "password": "testpassword3"}
    )
    test_user3_id = test_user3_response.json()["id"]

    # Add the third user to the chat
    response = await client.post(
        f"/api/v1/chats/{chat_id}/members",
        headers=auth_header,
        json={"user_id": test_user3_id}
    )
    assert response.status_code == 200, f"Failed to add member: {response.text}"
    data = response.json()
    assert len(data["members"]) == 2, f"Expected 2 members, got {len(data['members'])}"
    member_ids = [member["id"] for member in data["members"]]
    assert test_user.id in member_ids, f"test_user not in members: {member_ids}"
    assert test_user3_id in member_ids, f"test_user3 not in members: {member_ids}"