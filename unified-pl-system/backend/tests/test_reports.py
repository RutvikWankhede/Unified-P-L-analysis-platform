

def test_reports_endpoints(client):
    # Public endpoints (no auth enforced on reports router currently)
    response = client.get("/api/v1/reports/csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    response2 = client.get("/api/v1/reports/executive")
    assert response2.status_code == 200
    assert "text/html" in response2.headers["content-type"]

    response3 = client.get("/api/v1/reports/pdf")
    assert response3.status_code == 200
    assert "application/pdf" in response3.headers["content-type"]
