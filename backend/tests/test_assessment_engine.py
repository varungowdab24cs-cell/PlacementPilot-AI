from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import AssessmentAttempt, Question, StudentAnswer


def create_catalog(client: TestClient) -> tuple[dict[str, object], dict[str, object]]:
    subject_response = client.post(
        "/subjects",
        json={"name": f"Test Subject {uuid4().hex}", "description": "Test catalog"},
    )
    assert subject_response.status_code == 201
    subject = subject_response.json()

    topic_response = client.post(
        "/topics",
        json={"subject_id": subject["id"], "name": f"Test Topic {uuid4().hex}"},
    )
    assert topic_response.status_code == 201
    return subject, topic_response.json()


def create_question(
    client: TestClient,
    topic_id: int,
    prompt: str,
    correct_answer: str,
) -> dict[str, object]:
    response = client.post(
        "/questions",
        json={
            "topic_id": topic_id,
            "prompt": prompt,
            "difficulty": "medium",
            "options": ["A", "B", "C", "D"],
            "correct_answer": correct_answer,
            "explanation": "The server stores this explanation.",
            "estimated_solving_time_seconds": 60,
            "is_sample": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def register_and_login(client: TestClient) -> str:
    email = f"{uuid4().hex}@example.com"
    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Assessment Student",
            "email": email,
            "password": "assessment-password",
        },
    )
    assert registration.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "assessment-password"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def test_question_crud_filtering_and_answer_key_protection() -> None:
    with TestClient(app) as client:
        subject, topic = create_catalog(client)
        question = create_question(client, topic["id"], "Which option is correct?", "B")

        assert "correct_answer" not in question
        assert "explanation" not in question

        filtered = client.get(
            "/questions",
            params={"subject_id": subject["id"], "difficulty": "medium"},
        )
        assert filtered.status_code == 200
        assert any(item["id"] == question["id"] for item in filtered.json())

        updated = client.patch(
            f"/questions/{question['id']}",
            json={"prompt": "Which updated option is correct?"},
        )
        deleted = client.delete(f"/questions/{question['id']}")

    assert updated.status_code == 200
    assert updated.json()["prompt"] == "Which updated option is correct?"
    assert "correct_answer" not in updated.json()
    assert deleted.status_code == 204


def test_assessment_start_submit_score_and_topic_summary() -> None:
    with TestClient(app) as client:
        subject, topic = create_catalog(client)
        first_question = create_question(client, topic["id"], "First question?", "A")
        second_question = create_question(client, topic["id"], "Second question?", "B")
        assessment_response = client.post(
            "/assessments",
            json={
                "subject_id": subject["id"],
                "title": "Sample assessment",
                "question_ids": [first_question["id"], second_question["id"]],
            },
        )
        assert assessment_response.status_code == 201
        assessment_id = assessment_response.json()["id"]

        token = register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        start = client.post(f"/assessments/{assessment_id}/start", headers=headers)
        assert start.status_code == 200
        start_data = start.json()
        assert all("correct_answer" not in question for question in start_data["questions"])
        assert all("explanation" not in question for question in start_data["questions"])

        submit = client.post(
            f"/assessments/{start_data['attempt_id']}/submit",
            headers=headers,
            json={
                "answers": [
                    {
                        "question_id": first_question["id"],
                        "selected_answer": "A",
                        "time_taken_seconds": 12,
                    },
                    {
                        "question_id": second_question["id"],
                        "selected_answer": "A",
                        "time_taken_seconds": 20,
                    },
                ]
            },
        )

    assert submit.status_code == 200
    result = submit.json()
    assert result["score"] == 50.0
    assert result["answered_questions"] == 2
    assert result["answers"][0]["correct_answer"] == "A"
    assert result["answers"][1]["is_correct"] is False
    assert result["topic_performance"][0]["correct_answers"] == 1
    assert result["topic_performance"][0]["score"] == 50.0

    with SessionLocal() as db:
        attempt = db.get(AssessmentAttempt, start_data["attempt_id"])
        answers = list(
            db.scalars(
                select(StudentAnswer).where(
                    StudentAnswer.attempt_id == start_data["attempt_id"]
                )
            ).all()
        )
        assert attempt is not None
        assert attempt.score == 50
        assert {answer.time_taken_seconds for answer in answers} == {12, 20}
        assert {answer.is_correct for answer in answers} == {True, False}


def test_student_cannot_submit_another_students_attempt() -> None:
    with TestClient(app) as client:
        _, topic = create_catalog(client)
        question = create_question(client, topic["id"], "Ownership question?", "C")
        assessment = client.post(
            "/assessments",
            json={"title": "Ownership assessment", "question_ids": [question["id"]]},
        ).json()

        first_token = register_and_login(client)
        first_start = client.post(
            f"/assessments/{assessment['id']}/start",
            headers={"Authorization": f"Bearer {first_token}"},
        ).json()
        second_token = register_and_login(client)
        response = client.post(
            f"/assessments/{first_start['attempt_id']}/submit",
            headers={"Authorization": f"Bearer {second_token}"},
            json={
                "answers": [
                    {
                        "question_id": question["id"],
                        "selected_answer": "C",
                        "time_taken_seconds": 10,
                    }
                ]
            },
        )

    assert response.status_code == 404
