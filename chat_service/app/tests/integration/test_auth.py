import asyncio

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
    assert response.json()["username"] == "newuser"
    assert response.json()["email"] == "newuser@example.com"


async def test_register_duplicate_username(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": test_user.username, "email": "another@example.com", "password": "newpassword"}
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


async def test_register_duplicate_email(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "uniqueuser", "email": test_user.email, "password": "newpassword"}
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


async def test_register_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "invaliduser", "email": "notanemail", "password": "newpassword"}
    )
    assert response.status_code == 422


async def test_register_short_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "shortpwuser", "email": "short@example.com", "password": "short"}
    )
    assert response.status_code == 422


async def test_login_user(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert response.json()["token_type"] == "bearer"


async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistentuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


async def test_login_inactive_user(client: AsyncClient, test_user):
    # Authenticate as the test user to get an access token
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Deactivate the user using the API endpoint
    update_response = await client.put(
        "/api/v1/users/me",
        json={"is_active": False},
        headers=headers
    )

    assert update_response.status_code == 200

    # Attempt to login again with the same credentials
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 401
    assert "Inactive user" in response.json()["detail"]


async def test_refresh_token(client: AsyncClient, test_user):
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    refresh_token = login_response.json()["refresh_token"]
    original_access_token = login_response.json()["access_token"]

    await asyncio.sleep(1)

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()
    new_access_token = refresh_response.json()["access_token"]

    assert new_access_token != original_access_token


async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


async def test_refresh_token_reuse(client: AsyncClient, test_user):
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    refresh_token = login_response.json()["refresh_token"]

    # Use refresh token once
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200

    # Try to use the same refresh token again
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200  # Will return a new access token


async def test_access_token_expiration(client: AsyncClient, test_user, app_config):
    original_expire_minutes = app_config.ACCESS_TOKEN_EXPIRE_MINUTES
    app_config.ACCESS_TOKEN_EXPIRE_MINUTES = 0.05  # 3 seconds

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    access_token = login_response.json()["access_token"]

    await asyncio.sleep(4)

    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 401

    app_config.ACCESS_TOKEN_EXPIRE_MINUTES = original_expire_minutes


async def test_refresh_token_expiration(client: AsyncClient, test_user, app_config):
    original_expire_days = app_config.REFRESH_TOKEN_EXPIRE_DAYS
    app_config.REFRESH_TOKEN_EXPIRE_DAYS = 1 / 86400  # 1 second in days

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    refresh_token = login_response.json()["refresh_token"]

    await asyncio.sleep(2)

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401
    assert "Invalid refresh token" in refresh_response.json()["detail"]

    app_config.REFRESH_TOKEN_EXPIRE_DAYS = original_expire_days


async def test_logout(client: AsyncClient, auth_header):
    response = await client.post("/api/v1/auth/logout", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}

    await asyncio.sleep(0.1)

    me_response = await client.get("/api/v1/users/me", headers=auth_header)
    assert me_response.status_code == 401


async def test_logout_invalid_token(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401


async def test_password_hashing(client: AsyncClient):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"username": "hashtest", "email": "hashtest@example.com", "password": "testpassword"}
    )
    assert register_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "hashtest", "password": "testpassword"}
    )
    assert login_response.status_code == 200

    user_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"}
    )
    assert "password" not in user_response.json()
    assert "hashed_password" not in user_response.json()


async def test_multiple_login_sessions(client: AsyncClient, test_user, db_session):
    # Login from two different "devices"
    login1 = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    login2 = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )

    assert login1.status_code == 200
    assert login2.status_code == 200
    assert login1.json()["access_token"] != login2.json()["access_token"]

    # The first token should now be invalid
    me1 = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login1.json()['access_token']}"}
    )
    assert me1.status_code == 401  # Unauthorized

    # The second token should be valid
    me2 = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login2.json()['access_token']}"}
    )
    assert me2.status_code == 200


async def test_login_case_insensitive_username(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username.upper(), "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
