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
    
    upload_id = data["upload_id"]
    mapping = {}
    for orig, val in data["analysis"]["suggested_mapping"].items():
        mapping[orig] = val["mapped_to"]
        
    finalize_res = client.post(
        "/api/v1/pl/finalize-upload",
        headers=headers,
        json={"upload_id": upload_id, "mapping": mapping, "filename": "test.csv"},
    )
    assert finalize_res.status_code == 201
    # Check if we can retrieve it
    response2 = client.get("/api/v1/pl/records", headers=headers)
    assert response2.status_code == 200


def test_upload_messy_csv_data(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass", "email": "test@test.com"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Semicolon delimited, leading/trailing empty lines, European amount formatting, and wide format (Sales & Spend)
    csv_content = (
        b"\n\n"
        b"Posting Date;Dept;Sales;Spend\n"
        b"2026-05-12;Retail; 12.500,50; (4.200,00)\n"
        b"\n"
    )
    files = {"file": ("messy.csv", csv_content, "text/csv")}

    response = client.post("/api/v1/pl/upload", headers=headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert "upload_id" in data

    upload_id = data["upload_id"]
    mapping = {}
    for orig, val in data["analysis"]["suggested_mapping"].items():
        mapping[orig] = val["mapped_to"]

    # Explicitly map them for the manual finalize test
    mapping["Posting Date"] = "date"
    mapping["Dept"] = "department"
    mapping["Sales"] = "Revenue"
    mapping["Spend"] = "Expense"

    finalize_res = client.post(
        "/api/v1/pl/finalize-upload",
        headers=headers,
        json={"upload_id": upload_id, "mapping": mapping, "filename": "messy.csv"},
    )
    assert finalize_res.status_code == 201
    assert finalize_res.json()["records_ingested"] == 2
