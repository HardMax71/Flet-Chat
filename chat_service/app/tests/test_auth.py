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


async def test_register_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "invaliduser", "email": "notanemail", "password": "newpassword"}
    )
    assert response.status_code == 422  # Unprocessable Entity


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


async def test_refresh_token(client: AsyncClient, test_user):
    # First, login to get tokens
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    refresh_token = login_response.json()["refresh_token"]
    original_access_token = login_response.json()["access_token"]

    print(f"Original access token: {original_access_token}")

    # Add a small delay
    await asyncio.sleep(1)

    # Use refresh token to get new access token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()
    new_access_token = refresh_response.json()["access_token"]

    print(f"New access token: {new_access_token}")

    assert new_access_token != original_access_token, "New access token should be different from the original"


async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


async def test_access_token_expiration(client: AsyncClient, test_user, app_config):
    # Set a very short expiration time for testing
    original_expire_minutes = app_config.ACCESS_TOKEN_EXPIRE_MINUTES
    app_config.ACCESS_TOKEN_EXPIRE_MINUTES = 0.05  # 3 seconds

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    access_token = login_response.json()["access_token"]

    # Wait for token to expire
    await asyncio.sleep(4)

    # Try to use expired token
    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 401

    # Reset the expiration time
    app_config.ACCESS_TOKEN_EXPIRE_MINUTES = original_expire_minutes


async def test_refresh_token_expiration(client: AsyncClient, test_user, app_config):
    original_expire_days = app_config.REFRESH_TOKEN_EXPIRE_DAYS
    app_config.REFRESH_TOKEN_EXPIRE_DAYS = 1 / 86400  # 1 second in days

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    print(f"Original refresh token: {refresh_token}")

    # Wait for token to expire (2 seconds)
    await asyncio.sleep(2)

    # Try to use expired refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401
    assert "Invalid refresh token" in refresh_response.json()["detail"]

    print(f"Refresh response: {refresh_response.json()}")

    # Reset the expiration time
    app_config.REFRESH_TOKEN_EXPIRE_DAYS = original_expire_days


async def test_logout(client: AsyncClient, auth_header):
    response = await client.post("/api/v1/auth/logout", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}

    # Add a small delay to ensure changes are committed
    await asyncio.sleep(0.1)

    # Try to use the same token after logout
    me_response = await client.get("/api/v1/users/me", headers=auth_header)
    assert me_response.status_code == 401


async def test_password_hashing(client: AsyncClient):
    # Register a new user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"username": "hashtest", "email": "hashtest@example.com", "password": "testpassword"}
    )
    assert register_response.status_code == 200

    # Login with the new user
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "hashtest", "password": "testpassword"}
    )
    assert login_response.status_code == 200

    # Verify that the password is not stored in plain text
    user_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"}
    )
    assert "password" not in user_response.json()
    assert "hashed_password" not in user_response.json()
