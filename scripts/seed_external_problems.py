import json
from pathlib import Path

from sqlalchemy import select

from backend.app.database import SessionLocal, init_db
from backend.app.models import Resource, Subject, Topic

DATA_PATH = (
    Path(__file__).parents[1] / "data" / "resources" / "external_dsa_problems.json"
)


def _get_or_create_topic(db, subject: Subject, name: str) -> Topic:
    topic = db.scalar(
        select(Topic).where(Topic.subject_id == subject.id, Topic.name == name)
    )
    if topic is None:
        topic = Topic(subject_id=subject.id, name=name)
        db.add(topic)
        db.flush()
    return topic


def seed_external_problems() -> None:
    init_db()
    problems = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        for item in problems:
            subject = db.scalar(select(Subject).where(Subject.name == item["subject"]))
            if subject is None:
                subject = Subject(name=item["subject"])
                db.add(subject)
                db.flush()

            topic = _get_or_create_topic(db, subject, item["topic"])
            prerequisite_ids = [
                _get_or_create_topic(db, subject, name).id
                for name in item.get("prerequisite_topics", [])
            ]
            resource = db.scalar(
                select(Resource).where(Resource.official_url == item["official_url"])
            )
            values = {
                "topic_id": topic.id,
                "title": item["title"],
                "resource_type": "external_problem",
                "platform": item["platform"],
                "difficulty": item["difficulty"],
                "official_url": item["official_url"],
                "url": item["official_url"],
                "description": item.get("description"),
                "prerequisite_topic_ids": prerequisite_ids,
                "recommended_company_categories": item.get(
                    "recommended_company_categories", []
                ),
                "is_external": True,
            }
            if resource is None:
                db.add(Resource(**values))
            else:
                for field, value in values.items():
                    setattr(resource, field, value)
        db.commit()


if __name__ == "__main__":
    seed_external_problems()
