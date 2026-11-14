from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


def test_adaptive_endpoints_use_assessment_and_practice_history() -> None:
    with TestClient(app) as client:
        subject = client.post(
            "/subjects",
            json={"name": f"Adaptive Subject {uuid4().hex}"},
        ).json()
        topic = client.post(
            "/topics",
            json={"subject_id": subject["id"], "name": f"Adaptive Topic {uuid4().hex}"},
        ).json()
        question = client.post(
            "/questions",
            json={
                "topic_id": topic["id"],
                "prompt": "Adaptive question?",
                "difficulty": "easy",
                "options": ["A", "B"],
                "correct_answer": "A",
                "explanation": "A is correct.",
                "estimated_solving_time_seconds": 30,
            },
        ).json()
        assessment = client.post(
            "/assessments",
            json={"title": "Adaptive assessment", "question_ids": [question["id"]]},
        ).json()
        email = f"{uuid4().hex}@example.com"
        client.post(
            "/auth/register",
            json={
                "full_name": "Adaptive Student",
                "email": email,
                "password": "adaptive-password",
            },
        )
        token = client.post(
            "/auth/login",
            json={"email": email, "password": "adaptive-password"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        attempt = client.post(
            f"/assessments/{assessment['id']}/start",
            headers=headers,
        ).json()
        submission = client.post(
            f"/assessments/{attempt['attempt_id']}/submit",
            headers=headers,
            json={
                "answers": [
                    {
                        "question_id": question["id"],
                        "selected_answer": "B",
                        "time_taken_seconds": 18,
                    }
                ]
            },
        )
        mastery = client.get("/adaptive/mastery/topics", headers=headers)
        recommendations = client.get("/adaptive/recommendations", headers=headers)
        path = client.get("/adaptive/learning-path", headers=headers)

    assert submission.status_code == 200
    topic_mastery = next(item for item in mastery.json() if item["topic_id"] == topic["id"])
    assert topic_mastery["mastery_score"] is None
    assert topic_mastery["mastery_level"] == "Insufficient data"
    assert topic_mastery["assessment_count"] == 1
    assert any(item["topic_id"] == topic["id"] for item in recommendations.json())
    assert path.status_code == 200

    path_item = next(
        item for item in path.json()["items"] if item["topic_id"] == topic["id"]
    )
    with TestClient(app) as client:
        practice = client.post(
            "/adaptive/practice",
            headers=headers,
            json={
                "topic_id": topic["id"],
                "activity_type": "practice",
                "difficulty": "medium",
                "completed": True,
                "questions_completed": 1,
                "total_questions": 1,
                "learning_path_item_id": path_item["id"],
            },
        )
        updated_path = client.get("/adaptive/learning-path", headers=headers)

    assert practice.status_code == 201
    assert practice.json()["mastery"]["practice_completion"] == 100
    assert updated_path.json()["completed_items"] >= 1
