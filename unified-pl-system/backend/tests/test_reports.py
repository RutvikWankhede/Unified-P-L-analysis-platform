def test_reports_endpoints(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/reports/csv", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    response2 = client.get("/api/v1/reports/executive", headers=headers)
    assert response2.status_code == 200
    assert "text/html" in response2.headers["content-type"]

    response3 = client.get("/api/v1/reports/pdf", headers=headers)
    assert response3.status_code == 200
    assert "application/pdf" in response3.headers["content-type"]
