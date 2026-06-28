from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Enterprise P&L AI API is running" in response.json()["message"]
