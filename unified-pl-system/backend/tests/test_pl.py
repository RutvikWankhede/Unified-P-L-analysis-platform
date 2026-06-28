

def test_get_pl_records_empty(client):
    # Need to be authenticated for P&L routes
    # First login to get token
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/pl/records", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_upload_pl_data(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    csv_content = b"domain,period,line_item,amount,currency\nRetail,Q1,Revenue,1000,USD"
    files = {"file": ("test.csv", csv_content, "text/csv")}

    response = client.post("/api/v1/pl/upload", headers=headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert "upload_id" in data
    assert data["records_ingested"] == 1

    # Check if we can retrieve it
    response2 = client.get("/api/v1/pl/records", headers=headers)
    assert response2.status_code == 200
    assert len(response2.json()["items"]) == 1
