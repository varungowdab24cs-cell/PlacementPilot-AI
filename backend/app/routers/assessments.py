from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.dependencies import get_current_student
from backend.app.database import get_db
from backend.app.models import (
    Assessment,
    AssessmentAttempt,
    Experiment,
    ExperimentAssignment,
    Question,
    Student,
    StudentAnswer,
    Subject,
)
from backend.app.schemas.assessment import (
    AnswerResult,
    AssessmentCreate,
    AssessmentQuestion,
    AssessmentRead,
    AssessmentResult,
    AssessmentStartResponse,
    AssessmentHistoryRead,
    AssessmentSubmission,
    TopicPerformance,
)
from backend.app.services.assessment import (
    answer_is_correct,
    build_topic_performance,
)
from backend.app.services.mastery import recalculate_student_mastery

router = APIRouter(prefix="/assessments", tags=["assessments"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentStudent = Annotated[Student, Depends(get_current_student)]


def _assessment_response(assessment: Assessment) -> AssessmentRead:
    return AssessmentRead(
        id=assessment.id,
        subject_id=assessment.subject_id,
        title=assessment.title,
        description=assessment.description,
        question_count=len(assessment.questions),
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: AssessmentCreate,
    db: DatabaseSession,
) -> AssessmentRead:
    if payload.subject_id is not None and db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    questions = list(
        db.scalars(select(Question).where(Question.id.in_(payload.question_ids))).all()
    )
    questions_by_id = {question.id: question for question in questions}
    if len(questions_by_id) != len(payload.question_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more questions were not found",
        )
    if payload.subject_id is not None and any(
        question.topic.subject_id != payload.subject_id for question in questions
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All questions must belong to the assessment subject",
        )

    assessment = Assessment(
        subject_id=payload.subject_id,
        title=payload.title.strip(),
        description=payload.description,
        questions=[questions_by_id[question_id] for question_id in payload.question_ids],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return _assessment_response(assessment)


@router.get("", response_model=list[AssessmentRead])
def list_assessments(db: DatabaseSession) -> list[AssessmentRead]:
    assessments = list(
        db.scalars(
            select(Assessment)
            .options(selectinload(Assessment.questions))
            .order_by(Assessment.id)
        ).all()
    )
    return [_assessment_response(assessment) for assessment in assessments]


@router.get("/history", response_model=list[AssessmentHistoryRead])
def assessment_history(
    student: CurrentStudent,
    db: DatabaseSession,
) -> list[AssessmentHistoryRead]:
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.student_id == student.id,
                AssessmentAttempt.completed_at.is_not(None),
            )
            .options(
                selectinload(AssessmentAttempt.assessment),
                selectinload(AssessmentAttempt.answers),
            )
            .order_by(AssessmentAttempt.completed_at.desc())
        ).all()
    )
    return [
        AssessmentHistoryRead(
            attempt_id=attempt.id,
            assessment_id=attempt.assessment_id,
            assessment_title=attempt.assessment.title,
            score=attempt.score,
            answered_questions=len(attempt.answers),
            completed_at=attempt.completed_at,
        )
        for attempt in attempts
    ]


@router.post("/{assessment_id}/start", response_model=AssessmentStartResponse)
def start_assessment(
    assessment_id: int,
    student: CurrentStudent,
    db: DatabaseSession,
    experiment_id: Optional[int] = Query(default=None),
    phase: Optional[Literal["pre", "post"]] = Query(default=None),
) -> AssessmentStartResponse:
    assessment = db.scalar(
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(selectinload(Assessment.questions))
    )
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if not assessment.questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assessment has no questions",
        )

    if phase is not None and experiment_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An experiment is required when specifying an assessment phase",
        )
    if experiment_id is not None:
        assignment = db.scalar(
            select(ExperimentAssignment).where(
                ExperimentAssignment.experiment_id == experiment_id,
                ExperimentAssignment.student_id == student.id,
            )
        )
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student is not assigned to this experiment",
            )
        if db.get(Experiment, experiment_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    started_at = datetime.now(timezone.utc)
    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student.id,
        started_at=started_at,
        experiment_id=experiment_id,
        assessment_phase=phase,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    questions = [
        AssessmentQuestion(
            id=question.id,
            topic_id=question.topic_id,
            prompt=question.prompt,
            question_type=question.question_type,
            difficulty=question.difficulty,
            options=question.options,
            estimated_solving_time_seconds=question.estimated_solving_time_seconds,
        )
        for question in assessment.questions
    ]
    return AssessmentStartResponse(
        attempt_id=attempt.id,
        assessment_id=assessment.id,
        started_at=attempt.started_at,
        questions=questions,
    )


@router.post("/{attempt_id}/submit", response_model=AssessmentResult)
def submit_assessment(
    attempt_id: int,
    payload: AssessmentSubmission,
    student: CurrentStudent,
    db: DatabaseSession,
) -> AssessmentResult:
    attempt = db.scalar(
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
        )
        .options(
            selectinload(AssessmentAttempt.assessment)
            .selectinload(Assessment.questions)
            .selectinload(Question.topic)
        )
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found")
    if attempt.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment attempt has already been submitted",
        )

    questions_by_id = {question.id: question for question in attempt.assessment.questions}
    submitted_by_id = {answer.question_id: answer for answer in payload.answers}
    unknown_question_ids = set(submitted_by_id) - set(questions_by_id)
    if unknown_question_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Submission contains a question outside this assessment",
        )

    now = datetime.now(timezone.utc)
    answer_results: list[AnswerResult] = []
    submitted_summary: dict[int, tuple[bool, int]] = {}
    correct_count = 0
    for question_id, submitted_answer in submitted_by_id.items():
        question = questions_by_id[question_id]
        is_correct = answer_is_correct(
            submitted_answer.selected_answer,
            question.correct_answer,
        )
        correct_count += int(is_correct)
        submitted_summary[question_id] = (
            is_correct,
            submitted_answer.time_taken_seconds,
        )
        db.add(
            StudentAnswer(
                attempt_id=attempt.id,
                student_id=student.id,
                question_id=question_id,
                answer_text=submitted_answer.selected_answer,
                is_correct=is_correct,
                time_taken_seconds=submitted_answer.time_taken_seconds,
                answered_at=now,
            )
        )
        answer_results.append(
            AnswerResult(
                question_id=question_id,
                selected_answer=submitted_answer.selected_answer,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                is_correct=is_correct,
                time_taken_seconds=submitted_answer.time_taken_seconds,
            )
        )

    total_questions = len(questions_by_id)
    attempt.score = round(correct_count / total_questions * 100, 2)
    attempt.completed_at = now
    db.commit()

    result = AssessmentResult(
        attempt_id=attempt.id,
        assessment_id=attempt.assessment_id,
        score=attempt.score,
        total_questions=total_questions,
        answered_questions=len(submitted_by_id),
        completed_at=now,
        answers=answer_results,
        topic_performance=build_topic_performance(
            attempt.assessment.questions,
            submitted_summary,
        ),
    )
    recalculate_student_mastery(db, student.id)
    return result
