from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import Settings, get_settings
from backend.app.models import RecommendationHistory, TopicMastery


def build_learning_context(
    db: Session,
    student_id: int,
    topic_id: int | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    config = settings or get_settings()
    mastery_query = select(TopicMastery).where(TopicMastery.student_id == student_id)
    if topic_id is not None:
        mastery_query = mastery_query.where(TopicMastery.topic_id == topic_id)
    mastery_query = (
        mastery_query.options(selectinload(TopicMastery.topic))
        .order_by(TopicMastery.is_sufficient.asc(), TopicMastery.mastery_score.asc())
        .limit(config.ai_max_context_topics)
    )
    mastery = list(db.scalars(mastery_query).all())

    topic_ids = {record.topic_id for record in mastery}
    recommendations = list(
        db.scalars(
            select(RecommendationHistory)
            .where(
                RecommendationHistory.student_id == student_id,
                RecommendationHistory.status == "recommended",
            )
            .order_by(RecommendationHistory.created_at.desc())
            .limit(config.ai_max_context_topics)
        ).all()
    )
    for recommendation in recommendations:
        topic_ids.add(recommendation.topic_id)

    context = [
        {
            "topic_id": record.topic_id,
            "topic": record.topic.name,
            "mastery_level": record.mastery_level,
            "mastery_score": (
                round(record.mastery_score, 2)
                if record.is_sufficient and record.mastery_score is not None
                else None
            ),
            "accuracy": record.accuracy,
            "consistency": record.consistency,
            "practice_completion": record.practice_completion,
        }
        for record in mastery
    ]
    context.extend(
        {
            "topic_id": recommendation.topic_id,
            "recommended_activity": recommendation.title,
            "recommended_difficulty": recommendation.difficulty,
            "rationale": recommendation.rationale,
        }
        for recommendation in recommendations
        if recommendation.topic_id not in {item["topic_id"] for item in context}
    )
    return [item for item in context if item["topic_id"] in topic_ids]
