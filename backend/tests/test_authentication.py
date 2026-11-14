from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import Student


def registration_payload(email: str) -> dict[str, object]:
    return {
        "full_name": "Ada Lovelace",
        "email": email,
        "password": "correct horse battery staple",
        "department": "Computer Science",
        "semester": 6,
        "programming_language_preference": "Python",
        "target_company_categories": ["product", "fintech"],
        "preparation_goals": "Prepare for backend engineering roles",
    }


def register_student(client: TestClient) -> tuple[str, dict[str, object]]:
    email = f"{uuid4().hex}@example.com"
    response = client.post("/auth/register", json=registration_payload(email))
    assert response.status_code == 201
    return email, response.json()


def test_registration_hashes_password_and_does_not_expose_it() -> None:
    with TestClient(app) as client:
        email, profile = register_student(client)

    assert profile["email"] == email
    assert "password" not in profile
    assert "password_hash" not in profile
    assert profile["target_company_categories"] == ["product", "fintech"]

    with SessionLocal() as db:
        student = db.scalar(select(Student).where(Student.email == email))
        assert student is not None
        assert student.password_hash
        assert student.password_hash != "correct horse battery staple"


def test_duplicate_email_returns_conflict() -> None:
    email = f"{uuid4().hex}@example.com"
    with TestClient(app) as client:
        first = client.post("/auth/register", json=registration_payload(email))
        duplicate = client.post("/auth/register", json=registration_payload(email))

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_login_and_invalid_credentials() -> None:
    with TestClient(app) as client:
        email, _ = register_student(client)
        login = client.post(
            "/auth/login",
            json={"email": email, "password": "correct horse battery staple"},
        )
        invalid_login = client.post(
            "/auth/login",
            json={"email": email, "password": "wrong password"},
        )

    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["access_token"]
    assert invalid_login.status_code == 401


def test_protected_profile_requires_token_and_updates_own_data() -> None:
    with TestClient(app) as client:
        email, _ = register_student(client)
        login = client.post(
            "/auth/login",
            json={"email": email, "password": "correct horse battery staple"},
        )
        token = login.json()["access_token"]

        unauthorized = client.get("/students/me")
        profile = client.get(
            "/students/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        updated = client.patch(
            "/students/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": "Ada Byron Lovelace",
                "semester": 7,
                "target_company_categories": ["consulting", "startup"],
            },
        )

    assert unauthorized.status_code == 401
    assert profile.status_code == 200
    assert profile.json()["email"] == email
    assert "password_hash" not in profile.json()
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Ada Byron Lovelace"
    assert updated.json()["semester"] == 7
    assert updated.json()["target_company_categories"] == ["consulting", "startup"]
