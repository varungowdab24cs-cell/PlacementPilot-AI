from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_student
from backend.app.database import get_db
from backend.app.models import PracticeRecord, Resource, Student
from backend.app.schemas.external import (
    ExternalPracticeStatsRead,
    ExternalProblemAttemptCreate,
    ExternalProblemAttemptRead,
    ExternalProblemRead,
)
from backend.app.services.external_problems import (
    EXTERNAL_PROBLEM_TYPE,
    external_problem_query,
    practice_statistics,
    recommend_external_problems,
)
from backend.app.services.mastery import recalculate_student_mastery

router = APIRouter(prefix="/dsa", tags=["external DSA problems"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentStudent = Annotated[Student, Depends(get_current_student)]


def _read_problem(resource: Resource) -> ExternalProblemRead:
    if resource.topic is None or resource.official_url is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="External problem metadata is incomplete",
        )
    return ExternalProblemRead(
        id=resource.id,
        title=resource.title,
        platform=resource.platform,
        topic_id=resource.topic_id,
        topic_name=resource.topic.name,
        difficulty=resource.difficulty,
        official_url=resource.official_url,
        description=resource.description,
        prerequisite_topic_ids=resource.prerequisite_topic_ids or [],
        recommended_company_categories=resource.recommended_company_categories or [],
    )


@router.get("/problems", response_model=list[ExternalProblemRead])
def list_external_problems(
    db: DatabaseSession,
    platform: Optional[str] = Query(default=None),
    topic_id: Optional[int] = Query(default=None, gt=0),
    difficulty: Optional[str] = Query(default=None),
) -> list[ExternalProblemRead]:
    resources = db.scalars(
        external_problem_query(
            platform=platform,
            topic_id=topic_id,
            difficulty=difficulty,
        )
    ).all()
    return [_read_problem(resource) for resource in resources]


@router.get("/problems/recommendations", response_model=list[ExternalProblemRead])
def get_recommended_problems(
    student: CurrentStudent,
    db: DatabaseSession,
    platform: Optional[str] = Query(default=None),
    topic_id: Optional[int] = Query(default=None, gt=0),
    difficulty: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[ExternalProblemRead]:
    resources = recommend_external_problems(
        db,
        student,
        platform=platform,
        topic_id=topic_id,
        difficulty=difficulty,
        limit=limit,
    )
    return [_read_problem(resource) for resource in resources]


@router.get("/problems/{resource_id}", response_model=ExternalProblemRead)
def get_external_problem(resource_id: int, db: DatabaseSession) -> ExternalProblemRead:
    resource = db.scalar(
        external_problem_query().where(Resource.id == resource_id)
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="External problem not found")
    return _read_problem(resource)


@router.post(
    "/problems/{resource_id}/attempts",
    response_model=ExternalProblemAttemptRead,
    status_code=status.HTTP_201_CREATED,
)
def record_external_attempt(
    resource_id: int,
    payload: ExternalProblemAttemptCreate,
    student: CurrentStudent,
    db: DatabaseSession,
) -> ExternalProblemAttemptRead:
    resource = db.scalar(
        external_problem_query().where(Resource.id == resource_id)
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="External problem not found")
    solved = payload.outcome == "solved"
    record = PracticeRecord(
        student_id=student.id,
        topic_id=resource.topic_id,
        resource_id=resource.id,
        activity_type=EXTERNAL_PROBLEM_TYPE,
        difficulty=resource.difficulty,
        completed=solved,
        questions_completed=1 if solved else 0,
        total_questions=1,
        completed_at=datetime.now(timezone.utc) if solved else None,
        outcome=payload.outcome,
        solving_time_seconds=payload.solving_time_seconds,
        completion_source="self_reported",
        verified=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    recalculate_student_mastery(db, student.id, create_learning_path=False)
    return ExternalProblemAttemptRead(
        id=record.id,
        resource_id=record.resource_id,
        topic_id=record.topic_id,
        outcome=record.outcome,
        solving_time_seconds=record.solving_time_seconds,
        completion_source=record.completion_source,
        verified=record.verified,
        created_at=record.created_at,
    )


@router.get("/practice/history", response_model=list[ExternalProblemAttemptRead])
def get_external_practice_history(
    student: CurrentStudent,
    db: DatabaseSession,
    resource_id: Optional[int] = Query(default=None, gt=0),
) -> list[ExternalProblemAttemptRead]:
    query = (
        select(PracticeRecord)
        .where(
            PracticeRecord.student_id == student.id,
            PracticeRecord.resource_id.is_not(None),
        )
        .order_by(PracticeRecord.created_at.desc(), PracticeRecord.id.desc())
    )
    if resource_id is not None:
        query = query.where(PracticeRecord.resource_id == resource_id)
    records = db.scalars(query).all()
    return [
        ExternalProblemAttemptRead(
            id=record.id,
            resource_id=record.resource_id,
            topic_id=record.topic_id,
            outcome=record.outcome,
            solving_time_seconds=record.solving_time_seconds,
            completion_source=record.completion_source,
            verified=record.verified,
            created_at=record.created_at,
        )
        for record in records
    ]


@router.get("/practice/stats", response_model=ExternalPracticeStatsRead)
def get_external_practice_stats(
    student: CurrentStudent,
    db: DatabaseSession,
) -> ExternalPracticeStatsRead:
    records = db.scalars(
        select(PracticeRecord).where(
            PracticeRecord.student_id == student.id,
            PracticeRecord.resource_id.is_not(None),
        )
    ).all()
    return ExternalPracticeStatsRead(**practice_statistics(records))
