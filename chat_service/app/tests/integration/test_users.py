import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_read_users(client: AsyncClient, auth_header):
    response = await client.get("/api/v1/users/", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for user in data:
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "created_at" in user
        assert "is_active" in user


async def test_read_users_me(client: AsyncClient, auth_header, test_user):
    response = await client.get("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email


async def test_update_user(client: AsyncClient, auth_header):
    update_data = {
        "email": "newemail@example.com",
        "username": "newusername",
        "password": "newpassword123"
    }
    response = await client.put("/api/v1/users/me", headers=auth_header, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == update_data["email"]
    assert data["username"] == update_data["username"]

    # Try logging in with new credentials
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": update_data["username"], "password": update_data["password"]}
    )
    assert login_response.status_code == 200


async def test_delete_user(client: AsyncClient, auth_header):
    response = await client.delete("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 204

    # Try to access the deleted user's profile
    me_response = await client.get("/api/v1/users/me", headers=auth_header)
    assert me_response.status_code == 401


async def test_search_users(client: AsyncClient, auth_header, test_user2):
    response = await client.get(f"/api/v1/users/search?query={test_user2.username[:4]}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(user["username"] == test_user2.username for user in data)


async def test_user_filter_by_username(client: AsyncClient, auth_header, test_user):
    response = await client.get(f"/api/v1/users/?username={test_user.username[:4]}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(user["username"] == test_user.username for user in data)


async def test_user_pagination(client: AsyncClient, auth_header):
    # Create 20 users
    for i in range(20):
        await client.post(
            "/api/v1/auth/register",
            json={"username": f"testuser{i}", "email": f"testuser{i}@example.com", "password": "testpassword123"}
        )

    # Get first page
    response1 = await client.get("/api/v1/users/?skip=0&limit=10", headers=auth_header)
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1) == 10

    # Get second page
    response2 = await client.get("/api/v1/users/?skip=10&limit=10", headers=auth_header)
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 10

    # Ensure no duplicate users
    ids1 = {user["id"] for user in data1}
    ids2 = {user["id"] for user in data2}
    assert len(ids1.intersection(ids2)) == 0


async def test_update_user_partial(client: AsyncClient, auth_header):
    # Update only email
    response = await client.put("/api/v1/users/me", headers=auth_header, json={"email": "partial@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "partial@example.com"

    # Update only username
    response = await client.put("/api/v1/users/me", headers=auth_header, json={"username": "partialupdate"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "partialupdate"


async def test_update_user_invalid_data(client: AsyncClient, auth_header):
    # Try to update with invalid email
    response = await client.put("/api/v1/users/me", headers=auth_header, json={"email": "invalid-email"})
    assert response.status_code == 422

    # Try to update with short password
    response = await client.put("/api/v1/users/me", headers=auth_header, json={"password": "short"})
    assert response.status_code == 422


async def test_user_soft_delete(client: AsyncClient, auth_header):
    # Soft delete the user
    response = await client.put("/api/v1/users/me", headers=auth_header, json={"is_active": False})
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == False

    # Try to login with the deactivated user
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": data["username"], "password": "testpassword"}
    )
    assert login_response.status_code == 401
