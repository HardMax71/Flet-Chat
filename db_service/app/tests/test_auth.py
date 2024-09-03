# app/tests/test_auth.py
def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "email": "newuser@example.com", "password": "newpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"


def test_login_user(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# app/tests/test_users.py
def test_read_users_me(client, auth_header):
    response = client.get("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"


def test_update_user(client, auth_header):
    response = client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"email": "newemail@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newemail@example.com"
