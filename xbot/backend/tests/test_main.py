from fastapi.testclient import TestClient

from xbot.main import app

client = TestClient(app)


def test_read_main() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to XBot API Server"}


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
