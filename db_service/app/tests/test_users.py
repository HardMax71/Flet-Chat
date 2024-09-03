# app/tests/test_users.py

def test_read_users_me(client, db_session, test_user, auth_header):
    response = client.get("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email



def test_update_user(client, db_session, test_user, auth_header):
    response = client.put(
        "/api/v1/users/me",
        headers=auth_header,
        json={"email": "newemail@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newemail@example.com"
