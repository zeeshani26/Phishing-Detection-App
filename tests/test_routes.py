"""Smoke tests for HTTP routes."""
from main import __version__, app


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data.get("version") == __version__
    assert "model_available" in data


def test_home_returns_200():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200


def test_version_exported():
    assert isinstance(__version__, str)
    assert len(__version__) >= 3
