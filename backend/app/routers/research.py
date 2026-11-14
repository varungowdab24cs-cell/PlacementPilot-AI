import csv
import io
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.dependencies import get_current_student
from backend.app.database import get_db
from backend.app.models import Experiment, ExperimentAssignment, Student
from backend.app.schemas.research import (
    ExperimentAssignmentRead,
    ExperimentCreate,
    ExperimentRead,
    ExperimentSequenceRead,
    ResearchAggregateReport,
    StudentAnalyticsRead,
)
from backend.app.services.research import (
    aggregate_report,
    assignment_read,
    build_sequence,
    experiment_read,
    stable_assignment,
    student_analytics,
)

router = APIRouter(prefix="/research", tags=["research evaluation"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentStudent = Annotated[Student, Depends(get_current_student)]


def require_researcher_key(
    key: Annotated[Optional[str], Header(alias="X-Researcher-Key")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.researcher_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research reporting is not configured",
        )
    if key != settings.researcher_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Researcher access required",
        )


@router.post(
    "/experiments",
    response_model=ExperimentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    payload: ExperimentCreate,
    db: DatabaseSession,
    _: None = Depends(require_researcher_key),
) -> ExperimentRead:
    if payload.ends_at is not None and payload.ends_at <= payload.starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Experiment end must be after its start",
        )
    experiment = Experiment(
        name=payload.name.strip(),
        description=payload.description,
        configuration={"control_topic_ids": payload.control_topic_ids},
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(experiment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An experiment with this name already exists",
        ) from exc
    db.refresh(experiment)
    return experiment_read(experiment)


@router.get("/experiments", response_model=list[ExperimentRead])
def list_experiments(
    db: DatabaseSession,
    _: None = Depends(require_researcher_key),
) -> list[ExperimentRead]:
    experiments = db.scalars(select(Experiment).order_by(Experiment.starts_at.desc())).all()
    return [experiment_read(experiment) for experiment in experiments]


def _get_experiment(db: Session, experiment_id: int) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.post(
    "/experiments/{experiment_id}/assign",
    response_model=ExperimentAssignmentRead,
)
def assign_student(
    experiment_id: int,
    student: CurrentStudent,
    db: DatabaseSession,
) -> ExperimentAssignmentRead:
    experiment = _get_experiment(db, experiment_id)
    now = datetime.now(timezone.utc)
    if now < experiment.starts_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=409, detail="Experiment has not started")
    if experiment.ends_at is not None and now > experiment.ends_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=409, detail="Experiment has ended")
    return assignment_read(stable_assignment(db, experiment, student))


@router.get(
    "/experiments/{experiment_id}/sequence",
    response_model=ExperimentSequenceRead,
)
def get_student_sequence(
    experiment_id: int,
    student: CurrentStudent,
    db: DatabaseSession,
) -> ExperimentSequenceRead:
    experiment = _get_experiment(db, experiment_id)
    assignment = db.scalar(
        select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment_id,
            ExperimentAssignment.student_id == student.id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Student is not assigned to this experiment")
    return build_sequence(db, experiment, assignment, student.id)


@router.get("/student-analytics", response_model=StudentAnalyticsRead)
def get_student_analytics(
    student: CurrentStudent,
    db: DatabaseSession,
) -> StudentAnalyticsRead:
    return student_analytics(db, student.id)


@router.get(
    "/experiments/{experiment_id}/report",
    response_model=ResearchAggregateReport,
)
def get_aggregate_report(
    experiment_id: int,
    db: DatabaseSession,
    _: None = Depends(require_researcher_key),
) -> ResearchAggregateReport:
    return aggregate_report(db, _get_experiment(db, experiment_id))


@router.get("/experiments/{experiment_id}/report.csv")
def export_aggregate_report(
    experiment_id: int,
    db: DatabaseSession,
    _: None = Depends(require_researcher_key),
) -> StreamingResponse:
    report = aggregate_report(db, _get_experiment(db, experiment_id))
    rows = []
    for group in report.groups:
        rows.append(
            {
                "experiment_id": report.experiment_id,
                "experiment_name": report.experiment_name,
                "condition": group.condition,
                "participant_count": group.participant_count,
                "pre_test_n": group.pre_test.n,
                "pre_test_mean": group.pre_test.mean,
                "pre_test_standard_deviation": group.pre_test.standard_deviation,
                "pre_test_ci_low": group.pre_test.confidence_interval_low,
                "pre_test_ci_high": group.pre_test.confidence_interval_high,
                "post_test_n": group.post_test.n,
                "post_test_mean": group.post_test.mean,
                "post_test_standard_deviation": group.post_test.standard_deviation,
                "post_test_ci_low": group.post_test.confidence_interval_low,
                "post_test_ci_high": group.post_test.confidence_interval_high,
                "improvement_n": group.improvement.n,
                "improvement_mean": group.improvement.mean,
                "improvement_standard_deviation": group.improvement.standard_deviation,
                "improvement_ci_low": group.improvement.confidence_interval_low,
                "improvement_ci_high": group.improvement.confidence_interval_high,
                "assessment_completion_mean": group.assessment_completion.mean,
                "dsa_solved_mean": group.dsa_solved.mean,
                "topic_mastery_change_mean": group.topic_mastery_change.mean,
            }
        )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else ["experiment_id"])
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="experiment_{experiment_id}_report.csv"'
        },
    )
