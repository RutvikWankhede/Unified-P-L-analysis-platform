def test_anomalies_endpoints(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First, upload a CSV file to get an upload_id
    csv_content = b"domain,period,line_item,amount,currency\nRetail,Q1,Revenue,1000,USD"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    response = client.post("/api/v1/pl/upload", headers=headers, files=files)
    assert response.status_code == 201
    upload_id = response.json()["upload_id"]

    # Run anomaly detection
    res = client.post(
        f"/api/v1/anomalies/detect?upload_id={upload_id}", headers=headers
    )
    assert res.status_code == 201
    assert "anomalies_detected" in res.json()

    # Get anomalies
    res = client.get("/api/v1/anomalies/", headers=headers)
    assert res.status_code == 200
    anomalies = res.json()
    assert isinstance(anomalies, list)

    if anomalies:
        anomaly_id = anomalies[0]["id"]
        res_detail = client.get(f"/api/v1/anomalies/{anomaly_id}", headers=headers)
        assert res_detail.status_code == 200
        assert "pl_record" in res_detail.json()
