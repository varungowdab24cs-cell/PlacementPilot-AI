from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


def test_student_assessment_adaptive_workflow() -> None:
    email = f"{uuid4().hex}@example.com"
    with TestClient(app) as client:
        registration = client.post(
            "/auth/register",
            json={
                "full_name": "Workflow Student",
                "email": email,
                "password": "correct horse battery staple",
            },
        )
        token = client.post(
            "/auth/login",
            json={"email": email, "password": "correct horse battery staple"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        subject = client.post(
            "/subjects",
            json={"name": f"Workflow Subject {uuid4().hex}"},
        ).json()
        topic = client.post(
            "/topics",
            json={"subject_id": subject["id"], "name": f"Workflow Topic {uuid4().hex}"},
        ).json()
        question = client.post(
            "/questions",
            json={
                "topic_id": topic["id"],
                "prompt": "Which value is correct?",
                "difficulty": "easy",
                "options": ["correct", "incorrect"],
                "correct_answer": "correct",
                "estimated_solving_time_seconds": 30,
            },
        ).json()
        assessment = client.post(
            "/assessments",
            json={
                "subject_id": subject["id"],
                "title": "Workflow benchmark",
                "question_ids": [question["id"]],
            },
        ).json()
        started = client.post(
            f"/assessments/{assessment['id']}/start",
            headers=headers,
        ).json()
        result = client.post(
            f"/assessments/{started['attempt_id']}/submit",
            headers=headers,
            json={
                "answers": [
                    {
                        "question_id": question["id"],
                        "selected_answer": "correct",
                        "time_taken_seconds": 12,
                    }
                ]
            },
        )
        mastery_before_practice = client.get("/adaptive/mastery", headers=headers)
        practice = client.post(
            "/adaptive/practice",
            headers=headers,
            json={
                "topic_id": topic["id"],
                "activity_type": "practice",
                "difficulty": "easy",
                "completed": True,
                "questions_completed": 1,
                "total_questions": 1,
            },
        )
        mastery_after_practice = client.get("/adaptive/mastery", headers=headers)
        history = client.get("/assessments/history", headers=headers)

    assert registration.status_code == 201
    assert result.status_code == 200
    assert result.json()["score"] == 100
    assert mastery_before_practice.status_code == 200
    assert practice.status_code == 201
    topic_mastery = next(
        item
        for item in mastery_after_practice.json()["topics"]
        if item["topic_id"] == topic["id"]
    )
    assert topic_mastery["practice_completion"] == 100
    assert history.status_code == 200
    assert history.json()[0]["score"] == 100
