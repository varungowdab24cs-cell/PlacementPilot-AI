from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from backend.app.database import engine
from backend.app.main import app


def test_database_connectivity_and_schema() -> None:
    expected_tables = {
        "students",
        "subjects",
        "topics",
        "questions",
        "assessments",
        "assessment_attempts",
        "student_answers",
        "topic_mastery",
        "learning_paths",
        "resources",
        "chat_sessions",
        "chat_messages",
    }

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        assert expected_tables.issubset(inspect(connection).get_table_names())


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        cors_response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert cors_response.status_code == 200
    assert cors_response.headers["access-control-allow-origin"] == "http://localhost:8501"
