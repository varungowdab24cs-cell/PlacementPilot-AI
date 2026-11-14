from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import Resource, Subject, Topic


def _create_problem_set() -> tuple[int, int]:
    suffix = uuid4().hex
    with SessionLocal() as db:
        subject = Subject(name=f"DSA {suffix}")
        db.add(subject)
        db.flush()
        topic = Topic(subject_id=subject.id, name=f"Arrays {suffix}")
        db.add(topic)
        db.flush()
        first = Resource(
            topic_id=topic.id,
            title="Two Sum",
            resource_type="external_problem",
            platform="leetcode",
            difficulty="easy",
            official_url="https://leetcode.com/problems/two-sum/",
            description="Find two indices with a target sum.",
            prerequisite_topic_ids=[],
            recommended_company_categories=["product"],
            is_external=True,
        )
        second = Resource(
            topic_id=topic.id,
            title="Array Walk",
            resource_type="external_problem",
            platform="codeforces",
            difficulty="medium",
            official_url="https://codeforces.com/problemset/problem/1/A",
            prerequisite_topic_ids=[],
            recommended_company_categories=["service"],
            is_external=True,
        )
        db.add_all([first, second])
        db.commit()
        return first.id, topic.id


def _register(client: TestClient) -> str:
    email = f"{uuid4().hex}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Donald Knuth",
            "email": email,
            "password": "correct horse battery staple",
            "target_company_categories": ["product"],
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )
    return login.json()["access_token"]


def test_external_problem_filters_and_mastery_recommendations() -> None:
    first_id, topic_id = _create_problem_set()
    with TestClient(app) as client:
        filtered = client.get(
            f"/dsa/problems?platform=leetcode&difficulty=easy&topic_id={topic_id}"
        )
        token = _register(client)
        recommended = client.get(
            f"/dsa/problems/recommendations?topic_id={topic_id}&limit=1",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert filtered.status_code == 200
    assert [problem["id"] for problem in filtered.json()] == [first_id]
    assert recommended.status_code == 200
    assert recommended.json()[0]["topic_id"] == topic_id
    assert recommended.json()[0]["official_url"].startswith("https://")


def test_external_completion_is_self_reported_and_updates_stats() -> None:
    resource_id, topic_id = _create_problem_set()
    with TestClient(app) as client:
        token = _register(client)
        headers = {"Authorization": f"Bearer {token}"}
        solved = client.post(
            f"/dsa/problems/{resource_id}/attempts",
            headers=headers,
            json={"outcome": "solved", "solving_time_seconds": 95},
        )
        skipped = client.post(
            f"/dsa/problems/{resource_id}/attempts",
            headers=headers,
            json={"outcome": "skipped"},
        )
        history = client.get("/dsa/practice/history", headers=headers)
        stats = client.get("/dsa/practice/stats", headers=headers)

    assert solved.status_code == 201
    assert solved.json()["completion_source"] == "self_reported"
    assert solved.json()["verified"] is False
    assert solved.json()["topic_id"] == topic_id
    assert skipped.status_code == 201
    assert len(history.json()) == 2
    assert stats.json()["solved"] == 1
    assert stats.json()["skipped"] == 1
    assert stats.json()["average_solving_time_seconds"] == 95
    assert stats.json()["self_reported_count"] == 2

    with SessionLocal() as db:
        records = db.scalars(
            select(Resource).where(Resource.id == resource_id)
        ).all()
        assert len(records) == 1
