from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


def _register(client: TestClient) -> str:
    email = f"{uuid4().hex}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Research Participant",
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )
    return login.json()["access_token"]


def _experiment_payload(name: str) -> dict[str, object]:
    return {
        "name": name,
        "description": "Comparable pre/post evaluation.",
        "starts_at": "2026-01-01T00:00:00Z",
        "ends_at": "2027-01-01T00:00:00Z",
        "control_topic_ids": [1, 2],
    }


def test_assignment_is_stable_and_student_analytics_preserves_missing_scores() -> None:
    with TestClient(app) as client:
        token = _register(client)
        key_headers = {"X-Researcher-Key": "test-researcher-key"}
        experiment = client.post(
            "/research/experiments",
            headers=key_headers,
            json=_experiment_payload(f"Missing data {uuid4().hex}"),
        )
        experiment_id = experiment.json()["id"]
        headers = {"Authorization": f"Bearer {token}"}
        first = client.post(
            f"/research/experiments/{experiment_id}/assign",
            headers=headers,
        )
        second = client.post(
            f"/research/experiments/{experiment_id}/assign",
            headers=headers,
        )
        analytics = client.get("/research/student-analytics", headers=headers)
        sequence = client.get(
            f"/research/experiments/{experiment_id}/sequence",
            headers=headers,
        )

    assert experiment.status_code == 201
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["condition"] == second.json()["condition"]
    assert analytics.status_code == 200
    assert analytics.json()["pre_test_score"] is None
    assert analytics.json()["post_test_score"] is None
    assert sequence.status_code == 200
    assert sequence.json()["condition"] in {"control", "experimental"}


def test_aggregate_report_is_anonymized_and_does_not_fabricate_scores() -> None:
    with TestClient(app) as client:
        token = _register(client)
        key_headers = {"X-Researcher-Key": "test-researcher-key"}
        experiment = client.post(
            "/research/experiments",
            headers=key_headers,
            json=_experiment_payload(f"Aggregate {uuid4().hex}"),
        )
        experiment_id = experiment.json()["id"]
        assigned = client.post(
            f"/research/experiments/{experiment_id}/assign",
            headers={"Authorization": f"Bearer {token}"},
        )
        report = client.get(
            f"/research/experiments/{experiment_id}/report",
            headers=key_headers,
        )
        csv_report = client.get(
            f"/research/experiments/{experiment_id}/report.csv",
            headers=key_headers,
        )

    assert assigned.status_code == 200
    assert report.status_code == 200
    group = next(
        item
        for item in report.json()["groups"]
        if item["condition"] == assigned.json()["condition"]
    )
    assert group["participant_count"] == 1
    assert group["pre_test"]["n"] == 0
    assert group["pre_test"]["mean"] is None
    assert group["post_test"]["mean"] is None
    assert "Research Participant" not in csv_report.text
    assert "@" not in csv_report.text
    assert csv_report.headers["content-type"].startswith("text/csv")
