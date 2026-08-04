"""Run a small HTTP smoke test against a running PetroQuery API."""
from __future__ import annotations

import uuid

import httpx


def main() -> None:
    suffix = uuid.uuid4().hex[:10]
    username = f"e2e_{suffix}"
    password = f"E2e-{suffix}-Password!"

    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        response = client.get("/health")
        response.raise_for_status()

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": password,
            },
        )
        assert response.status_code == 201, response.text

        response = client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
        )
        assert response.status_code == 200, response.text
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200, response.text

        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": f"E2E Project {suffix}",
                "description": "HTTP smoke project",
                "cuenca": "Vaca Muerta",
                "ubicacion": "Neuquen",
            },
        )
        assert response.status_code == 201, response.text
        project_id = response.json()["id"]

        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200, response.text

        response = client.get("/documents", headers=headers)
        assert response.status_code == 200, response.text

        response = client.post(
            "/api/v1/ingest/pdf",
            headers=headers,
            data={"project_id": str(project_id)},
            files={"file": ("invalid.pdf", b"not a pdf", "application/pdf")},
        )
        assert response.status_code == 400, response.text

        response = client.post(
            "/api/v1/ingest/pdf",
            headers=headers,
            data={"project_id": str(project_id)},
            files={
                "file": (
                    "sample.pdf",
                    b"%PDF-1.4\nminimal smoke fixture",
                    "application/pdf",
                )
            },
        )
        assert response.status_code == 202, response.text

    print("E2E smoke passed: health, register, login, me, project, documents, upload")


if __name__ == "__main__":
    main()
