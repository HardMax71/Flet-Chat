import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "email": "newuser@example.com", "password": "newpassword"}
    )
    assert response.status_code == 200
    assert "id" in response.json()

async def test_login_user(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

async def test_read_users_me(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 200
    assert "username" in response.json()

async def test_update_user(client: AsyncClient, auth_header):
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"email": "newemail@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "newemail@example.com"