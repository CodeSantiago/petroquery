"""HTTP-level smoke tests for the public FastAPI surface."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models import User


def test_health_endpoint_is_public_and_reports_service_status():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["system"] == "PetroQuery"
    # ml_status is informational: it should always be present and be a
    # string so the operator can tell whether the optional ML stack is
    # installed on the host.
    assert "ml_status" in payload
    assert isinstance(payload["ml_status"], str)


def test_documents_endpoint_requires_authentication():
    response = TestClient(app).get("/documents")

    assert response.status_code == 401


def test_documents_query_is_scoped_to_project_membership():
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.unique.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    user = User(id=7, email="u@example.com", username="user", hashed_password="h")

    async def override_db():
        yield db

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        response = TestClient(app).get("/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    statement = str(db.execute.await_args.args[0])
    assert "project_members" in statement
    assert "documents" in statement
