import asyncio
import random

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_read_users_me(client: AsyncClient, test_user, auth_header):
    response = await client.get("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert "id" in data
    assert "created_at" in data
    assert "is_active" in data


async def test_update_user(client: AsyncClient, auth_header):
    new_email = f"newemail{random.randint(1, 1000000)}@example.com"
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"email": new_email}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == new_email


async def test_update_user_username(client: AsyncClient, auth_header):
    new_username = f"newuser{random.randint(1, 1000000)}"
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"username": new_username}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == new_username


async def test_update_user_password(client: AsyncClient, auth_header):
    new_password = "newpassword123"
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"password": new_password}
    )
    assert response.status_code == 200

    await asyncio.sleep(0.1)

    # Try to login with the new password
    user_data = response.json()
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_data["username"], "password": new_password}
    )
    assert login_response.status_code == 200


async def test_update_user_invalid_email(client: AsyncClient, auth_header):
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"email": "invalid_email"}
    )
    assert response.status_code == 422  # Unprocessable Entity


async def test_update_user_invalid_password(client: AsyncClient, auth_header):
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"password": "short"}
    )
    assert response.status_code == 422  # Unprocessable Entity


async def test_delete_user(client: AsyncClient, auth_header):
    response = await client.delete("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 204

    # Try to access the user's profile after deletion
    me_response = await client.get("/api/v1/users/me", headers=auth_header)
    assert me_response.status_code == 401  # Unauthorized


async def test_search_users(client: AsyncClient, auth_header, test_user2):
    response = await client.get(f"/api/v1/users/search?query={test_user2.username[:4]}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(user["username"] == test_user2.username for user in data)


async def test_search_users_no_results(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/users/search?query=nonexistentuser", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


async def test_get_all_users(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/users/", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(isinstance(user, dict) for user in data)
    assert all("id" in user and "username" in user and "email" in user for user in data)


async def test_get_all_users_with_pagination(client: AsyncClient, auth_header):
    # Create multiple users
    for i in range(5):
        await client.post(
            "/api/v1/auth/register",
            json={"username": f"testuser{i}", "email": f"testuser{i}@example.com", "password": "testpassword"}
        )

    response = await client.get("/api/v1/users/?skip=0&limit=3", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    response = await client.get("/api/v1/users/?skip=3&limit=3", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


async def test_get_all_users_with_username_filter(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/users/?username=test", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all("test" in user["username"].lower() for user in data)
