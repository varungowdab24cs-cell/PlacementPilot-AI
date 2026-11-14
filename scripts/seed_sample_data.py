import json
from pathlib import Path

from sqlalchemy import select

from backend.app.database import SessionLocal, init_db
from backend.app.models import Question, Subject, Topic

DATA_PATH = Path(__file__).parents[1] / "data" / "questions" / "sample_questions.json"


def seed_sample_data() -> None:
    init_db()
    sample_questions = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    with SessionLocal() as db:
        for item in sample_questions:
            subject = db.scalar(select(Subject).where(Subject.name == item["subject"]))
            if subject is None:
                subject = Subject(name=item["subject"])
                db.add(subject)
                db.flush()

            topic = db.scalar(
                select(Topic).where(
                    Topic.subject_id == subject.id,
                    Topic.name == item["topic"],
                )
            )
            if topic is None:
                topic = Topic(subject_id=subject.id, name=item["topic"])
                db.add(topic)
                db.flush()

            question_data = item["question"]
            exists = db.scalar(
                select(Question).where(
                    Question.topic_id == topic.id,
                    Question.prompt == question_data["prompt"],
                )
            )
            if exists is None:
                db.add(
                    Question(
                        topic_id=topic.id,
                        question_type="mcq",
                        is_sample=True,
                        **question_data,
                    )
                )

        db.commit()


if __name__ == "__main__":
    seed_sample_data()
