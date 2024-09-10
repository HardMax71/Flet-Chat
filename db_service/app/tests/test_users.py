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