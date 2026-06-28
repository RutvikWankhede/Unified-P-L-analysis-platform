def test_login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "wrong", "email": "test@test.com"},
    )
    assert response.status_code == 401


def test_forgot_password(client):
    response = client.post("/api/v1/auth/forgot-password?email=test@test.com")
    assert response.status_code == 200
    assert "link has been sent" in response.json()["message"]
