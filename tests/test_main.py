import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db",
)
os.environ.setdefault("SECRET_KEY", "test_secret_key")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_inicio_responde_mensaje_de_la_api():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"mensaje": "API de gestión de taller mecánico"}
