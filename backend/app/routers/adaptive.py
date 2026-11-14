from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.dependencies import get_current_student
from backend.app.database import get_db
from backend.app.models import (
    LearningPath,
    LearningPathItem,
    PracticeRecord,
    RecommendationHistory,
    Student,
    Topic,
    TopicMastery,
)
from backend.app.schemas.adaptive import (
    LearningPathItemRead,
    LearningPathRead,
    MasteryRead,
    OverallMasteryRead,
    PracticeCreate,
    PracticeResponse,
    RecommendationRead,
)
from backend.app.services.mastery import (
    _mastery_read,
    learning_path_progress,
    recalculate_student_mastery,
)

router = APIRouter(prefix="/adaptive", tags=["adaptive learning"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentStudent = Annotated[Student, Depends(get_current_student)]


def _load_mastery(db: Session, student_id: int) -> list[TopicMastery]:
    return list(
        db.scalars(
            select(TopicMastery)
            .where(TopicMastery.student_id == student_id)
            .options(selectinload(TopicMastery.topic))
            .order_by(TopicMastery.topic_id)
        ).all()
    )


@router.get("/mastery", response_model=OverallMasteryRead)
def get_overall_mastery(
    student: CurrentStudent,
    db: DatabaseSession,
) -> OverallMasteryRead:
    records = _load_mastery(db, student.id)
    topics = [_mastery_read(record) for record in records]
    scored = [topic.mastery_score for topic in topics if topic.mastery_score is not None]
    return OverallMasteryRead(
        overall_score=round(sum(scored) / len(scored), 2) if scored else None,
        classified_topics=len(scored),
        total_topics=len(topics),
        sufficient_history=bool(topics) and all(topic.is_sufficient for topic in topics),
        topics=topics,
    )


@router.get("/mastery/topics", response_model=list[MasteryRead])
def get_topic_mastery(
    student: CurrentStudent,
    db: DatabaseSession,
) -> list[MasteryRead]:
    return [_mastery_read(record) for record in _load_mastery(db, student.id)]


@router.get("/weak-topics", response_model=list[MasteryRead])
def get_weak_topics(
    student: CurrentStudent,
    db: DatabaseSession,
) -> list[MasteryRead]:
    records = _load_mastery(db, student.id)
    return [
        _mastery_read(record)
        for record in records
        if record.mastery_level == "Weak"
    ]


@router.get("/recommendations", response_model=list[RecommendationRead])
def get_recommendations(
    student: CurrentStudent,
    db: DatabaseSession,
) -> list[RecommendationRead]:
    recommendations = list(
        db.scalars(
            select(RecommendationHistory)
            .where(
                RecommendationHistory.student_id == student.id,
                RecommendationHistory.status == "recommended",
            )
            .options(selectinload(RecommendationHistory.topic))
            .order_by(RecommendationHistory.id)
        ).all()
    )
    return [
        RecommendationRead(
            id=recommendation.id,
            topic_id=recommendation.topic_id,
            topic_name=recommendation.topic.name,
            activity_type=recommendation.activity_type,
            difficulty=recommendation.difficulty,
            title=recommendation.title,
            rationale=recommendation.rationale,
            status=recommendation.status,
            created_at=recommendation.created_at,
        )
        for recommendation in recommendations
    ]


@router.get("/learning-path", response_model=LearningPathRead)
def get_learning_path(
    student: CurrentStudent,
    db: DatabaseSession,
) -> LearningPathRead:
    path = db.scalar(
        select(LearningPath)
        .where(
            LearningPath.student_id == student.id,
            LearningPath.status == "active",
        )
        .options(selectinload(LearningPath.items).selectinload(LearningPathItem.topic))
        .order_by(LearningPath.id.desc())
    )
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active learning path exists",
        )
    completed, total, progress = learning_path_progress(path)
    return LearningPathRead(
        id=path.id,
        title=path.title,
        description=path.description,
        status=path.status,
        completed_items=completed,
        total_items=total,
        progress=progress,
        items=[
            LearningPathItemRead(
                id=item.id,
                topic_id=item.topic_id,
                topic_name=item.topic.name,
                title=item.title,
                activity_type=item.activity_type,
                difficulty=item.difficulty,
                rationale=item.rationale,
                position=item.position,
                status=item.status,
                completed_at=item.completed_at,
            )
            for item in sorted(path.items, key=lambda item: item.position)
        ],
    )


@router.post("/practice", response_model=PracticeResponse, status_code=status.HTTP_201_CREATED)
def record_practice(
    payload: PracticeCreate,
    student: CurrentStudent,
    db: DatabaseSession,
) -> PracticeResponse:
    if db.get(Topic, payload.topic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    path_item = None
    if payload.learning_path_item_id is not None:
        path_item = db.scalar(
            select(LearningPathItem)
            .join(LearningPath)
            .where(
                LearningPathItem.id == payload.learning_path_item_id,
                LearningPath.student_id == student.id,
            )
        )
        if path_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning path item not found",
            )
        if path_item.topic_id != payload.topic_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Practice topic does not match the learning path item",
            )

    completed_at = datetime.now(timezone.utc) if payload.completed else None
    record = PracticeRecord(
        student_id=student.id,
        topic_id=payload.topic_id,
        activity_type=payload.activity_type,
        difficulty=payload.difficulty,
        completed=payload.completed,
        questions_completed=payload.questions_completed,
        total_questions=payload.total_questions,
        completed_at=completed_at,
        learning_path_item_id=payload.learning_path_item_id,
    )
    db.add(record)
    if path_item is not None and payload.completed:
        path_item.status = "completed"
        path_item.completed_at = completed_at
    db.commit()
    db.refresh(record)

    mastery = recalculate_student_mastery(
        db,
        student.id,
        create_learning_path=False,
    )
    topic_mastery = next(
        (item for item in mastery if item.topic_id == payload.topic_id),
        None,
    )
    return PracticeResponse(
        id=record.id,
        topic_id=record.topic_id,
        completed=record.completed,
        mastery=topic_mastery,
    )


@router.post("/recalculate", response_model=list[MasteryRead])
def recalculate_mastery(
    student: CurrentStudent,
    db: DatabaseSession,
) -> list[MasteryRead]:
    return recalculate_student_mastery(db, student.id)
