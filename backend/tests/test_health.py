from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    """GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_returns_running():
    """GET / returns 200 with application name and status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "The Lenny Growth Assistant"
    assert data["status"] == "running"
