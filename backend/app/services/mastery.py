from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import get_settings
from backend.app.models import (
    Assessment,
    AssessmentAttempt,
    LearningPath,
    LearningPathItem,
    MasteryHistory,
    PracticeRecord,
    RecommendationHistory,
    Resource,
    Student,
    Topic,
    TopicMastery,
)
from backend.app.schemas.adaptive import MasteryRead
from backend.app.services.adaptive import (
    FORMULA_VERSION,
    MasteryCalculation,
    MasteryConfig,
    TopicMetrics,
    build_recommendation_drafts,
    calculate_consistency,
    calculate_mastery,
)


def collect_topic_metrics(db: Session, student_id: int) -> list[TopicMetrics]:
    topics = list(
        db.scalars(
            select(Topic)
            .options(selectinload(Topic.questions))
            .order_by(Topic.id)
        ).all()
    )
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.student_id == student_id,
                AssessmentAttempt.completed_at.is_not(None),
            )
            .options(
                selectinload(AssessmentAttempt.assessment).selectinload(Assessment.questions),
                selectinload(AssessmentAttempt.answers),
            )
        ).all()
    )
    practice_records = list(
        db.scalars(
            select(PracticeRecord).where(PracticeRecord.student_id == student_id)
        ).all()
    )

    attempt_scores: dict[int, list[float]] = defaultdict(list)
    for attempt in attempts:
        answers_by_question = {answer.question_id: answer for answer in attempt.answers}
        topic_totals: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        for question in attempt.assessment.questions:
            topic_totals[question.topic_id][0] += 1
            answer = answers_by_question.get(question.id)
            topic_totals[question.topic_id][1] += int(
                answer is not None and answer.is_correct is True
            )
        for topic_id, (total, correct) in topic_totals.items():
            if total:
                attempt_scores[topic_id].append(correct / total)

    practice_totals: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for record in practice_records:
        practice_totals[record.topic_id][0] += 1
        practice_totals[record.topic_id][1] += int(record.completed)

    metrics = []
    for topic in topics:
        scores = attempt_scores.get(topic.id, [])
        practice_total, practice_completed = practice_totals.get(topic.id, [0, 0])
        metrics.append(
            TopicMetrics(
                topic_id=topic.id,
                topic_name=topic.name,
                prerequisite_topic_id=topic.prerequisite_topic_id,
                accuracy=round(sum(scores) / len(scores) * 100, 2) if scores else None,
                consistency=calculate_consistency(scores),
                practice_completion=(
                    round(practice_completed / practice_total * 100, 2)
                    if practice_total
                    else None
                ),
                assessment_count=len(scores),
            )
        )
    return metrics


def _mastery_read(topic_mastery: TopicMastery) -> MasteryRead:
    return MasteryRead(
        topic_id=topic_mastery.topic_id,
        topic_name=topic_mastery.topic.name,
        mastery_score=(
            topic_mastery.mastery_score if topic_mastery.is_sufficient else None
        ),
        mastery_level=topic_mastery.mastery_level,
        accuracy=topic_mastery.accuracy,
        consistency=topic_mastery.consistency,
        practice_completion=topic_mastery.practice_completion,
        assessment_count=topic_mastery.assessment_count,
        is_sufficient=topic_mastery.is_sufficient,
        updated_at=topic_mastery.updated_at,
    )


def recalculate_student_mastery(
    db: Session,
    student_id: int,
    *,
    create_learning_path: bool = True,
) -> list[MasteryRead]:
    settings = get_settings()
    config = MasteryConfig.from_settings(settings)
    metrics = collect_topic_metrics(db, student_id)
    calculations = {
        metric.topic_id: calculate_mastery(metric, config) for metric in metrics
    }

    current_records = {
        record.topic_id: record
        for record in db.scalars(
            select(TopicMastery)
            .where(TopicMastery.student_id == student_id)
            .options(selectinload(TopicMastery.topic))
        ).all()
    }
    for metric in metrics:
        calculation = calculations[metric.topic_id]
        current = current_records.get(metric.topic_id)
        if current is None:
            current = TopicMastery(student_id=student_id, topic_id=metric.topic_id)
            db.add(current)
            current_records[metric.topic_id] = current
        current.mastery_score = calculation.score if calculation.score is not None else 0
        current.mastery_level = calculation.level
        current.is_sufficient = calculation.is_sufficient
        current.accuracy = metric.accuracy
        current.consistency = metric.consistency
        current.practice_completion = metric.practice_completion
        current.assessment_count = metric.assessment_count
        db.add(
            MasteryHistory(
                student_id=student_id,
                topic_id=metric.topic_id,
                mastery_score=calculation.score,
                mastery_level=calculation.level,
                is_sufficient=calculation.is_sufficient,
                accuracy=metric.accuracy,
                consistency=metric.consistency,
                practice_completion=metric.practice_completion,
                assessment_count=metric.assessment_count,
                formula_version=FORMULA_VERSION,
            )
        )

    db.flush()
    resource_titles: dict[int, str] = {}
    for resource in db.scalars(
        select(Resource)
        .where(Resource.topic_id.is_not(None))
        .order_by(Resource.id)
    ).all():
        if resource.topic_id is not None and resource.topic_id not in resource_titles:
            resource_titles[resource.topic_id] = resource.title
    drafts = build_recommendation_drafts(
        metrics,
        calculations,
        resource_titles,
        config,
    )
    db.execute(
        update(RecommendationHistory)
        .where(
            RecommendationHistory.student_id == student_id,
            RecommendationHistory.status == "recommended",
        )
        .values(status="superseded")
    )
    for draft in drafts:
        db.add(
            RecommendationHistory(
                student_id=student_id,
                topic_id=draft.topic_id,
                activity_type=draft.activity_type,
                difficulty=draft.difficulty,
                title=draft.title,
                rationale=draft.rationale,
                status="recommended",
            )
        )

    if create_learning_path and drafts:
        db.execute(
            update(LearningPath)
            .where(
                LearningPath.student_id == student_id,
                LearningPath.status == "active",
            )
            .values(status="superseded")
        )
        student = db.get(Student, student_id)
        path = LearningPath(
            student_id=student_id,
            title=f"Personalized path for {student.full_name if student else 'student'}",
            description="Deterministic recommendations based on current topic evidence.",
            status="active",
        )
        db.add(path)
        db.flush()
        for position, draft in enumerate(drafts, start=1):
            db.add(
                LearningPathItem(
                    learning_path_id=path.id,
                    topic_id=draft.topic_id,
                    title=draft.title,
                    activity_type=draft.activity_type,
                    difficulty=draft.difficulty,
                    rationale=draft.rationale,
                    position=position,
                )
            )

    db.commit()
    refreshed = list(
        db.scalars(
            select(TopicMastery)
            .where(TopicMastery.student_id == student_id)
            .options(selectinload(TopicMastery.topic))
            .order_by(TopicMastery.topic_id)
        ).all()
    )
    return [_mastery_read(record) for record in refreshed]


def learning_path_progress(path: LearningPath) -> tuple[int, int, float]:
    total = len(path.items)
    completed = sum(item.status == "completed" for item in path.items)
    return completed, total, round(completed / total * 100, 2) if total else 0
