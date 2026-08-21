from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Enterprise P&L AI API is running"}

def test_system_health():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_prometheus_metrics():
    response = client.get("/api/v1/system/metrics")
    assert response.status_code == 200
    assert "active_users" in response.json()
