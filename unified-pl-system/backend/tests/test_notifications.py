def test_notifications_endpoints(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get notifications (should be empty initially)
    res = client.get("/api/v1/notifications/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "unread_count" in data
    assert "notifications" in data

    # Test read non-existent notification
    res = client.post("/api/v1/notifications/9999/read", headers=headers)
    assert res.status_code == 404
