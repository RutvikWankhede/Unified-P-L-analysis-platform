

def test_explanations_endpoints(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # We might not have an anomaly with ID 9999, so it should 404
    res = client.post("/api/v1/explanations/generate/9999", headers=headers)
    assert res.status_code == 404

    # But we can test copilot chat
    res = client.post(
        "/api/v1/explanations/copilot",
        headers=headers,
        json={"question": "What is our total revenue?"},
    )
    assert res.status_code == 200
    assert "answer" in res.json()
