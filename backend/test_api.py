import os
from io import BytesIO

os.environ["JWT_SECRET_KEY"] = "test-only-signing-key-with-at-least-32-characters"
os.environ["CORS_ORIGINS"] = "https://careeriq-rho.vercel.app,http://localhost:5173"

import pytest
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from main import app, get_db, parse_cors_origins, validate_jwt_secret


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    def override_get_db():
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def create_docx_resume() -> bytes:
    document = Document()
    document.add_heading("Experience", level=1)
    document.add_paragraph("ada@example.com | +1 555 555 5555")
    document.add_paragraph("- Built Python and SQL backend services")
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def test_cors_preflight_supports_bearer_auth_and_rejects_unknown_origins(client):
    preflight = client.options(
        "/analyze-career",
        headers={
            "Origin": "https://careeriq-rho.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "https://careeriq-rho.vercel.app"
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "PUT" in preflight.headers["access-control-allow-methods"]
    assert "DELETE" in preflight.headers["access-control-allow-methods"]
    assert "authorization" in preflight.headers["access-control-allow-headers"].lower()
    assert preflight.headers.get("access-control-allow-credentials") != "true"

    rejected = client.options(
        "/analyze-career",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_environment_configuration_rejects_weak_secrets_and_wildcard_cors():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validate_jwt_secret(None)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validate_jwt_secret("too-short")
    assert len(validate_jwt_secret("a-random-secret-with-at-least-32-characters")) >= 32

    assert parse_cors_origins("https://careeriq-rho.vercel.app/") == [
        "https://careeriq-rho.vercel.app",
    ]
    with pytest.raises(RuntimeError, match="wildcard"):
        parse_cors_origins("*")
    with pytest.raises(RuntimeError, match="invalid origin"):
        parse_cors_origins("https://careeriq-rho.vercel.app/path")


def test_authenticated_analysis_and_history_are_private(client):
    registration = client.post(
        "/register",
        json={"name": "Ada Example", "email": "Ada@example.com", "password": "a-secure-test-password"},
    )
    assert registration.status_code == 200
    assert registration.json()["email"] == "ada@example.com"

    assert client.get("/user-history/ada@example.com").status_code == 401
    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/user-history/other@example.com", headers=headers).status_code == 403
    assert client.post(
        "/login",
        json={"email": "ada@example.com", "password": "incorrect-password"},
    ).status_code == 401

    response = client.post(
        "/analyze-career",
        headers=headers,
        data={"target_role": "Python Backend Developer"},
        files={"file": ("resume.docx", create_docx_resume(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["ats_analysis"]["score"] >= 0
    assert result["extracted_skills"] == ["Python", "SQL"]

    history = client.get("/user-history/ADA@example.com", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["filename"] == "resume.docx"
