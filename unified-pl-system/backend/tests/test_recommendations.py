def test_recommendations_endpoints(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload data first to create anomaly
    csv_content = b"domain,period,line_item,amount,currency\nRetail,Q1,Revenue,1000,USD"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    response = client.post("/api/v1/pl/upload", headers=headers, files=files)
    upload_id = response.json()["upload_id"]

    # Detect anomaly
    res = client.post(
        f"/api/v1/anomalies/detect?upload_id={upload_id}", headers=headers
    )
    assert res.status_code == 201

    # Fetch anomalies to find an ID
    res = client.get("/api/v1/anomalies/", headers=headers)
    anomalies = res.json()
    if anomalies:
        anomaly_id = anomalies[0]["id"]
        # Generate recommendations
        res = client.post(
            f"/api/v1/recommendations/generate/{anomaly_id}", headers=headers
        )
        assert res.status_code in [200, 201]

        # Get recommendations
        res = client.get(f"/api/v1/recommendations/{anomaly_id}", headers=headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)
    else:
        # Test with a mock ID
        res = client.get("/api/v1/recommendations/9999", headers=headers)
        assert res.status_code == 200
        assert res.json() == []
