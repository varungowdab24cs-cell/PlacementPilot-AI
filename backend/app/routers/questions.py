from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Question, Topic
from backend.app.schemas.assessment import (
    Difficulty,
    QuestionCreate,
    QuestionRead,
    QuestionUpdate,
)

router = APIRouter(prefix="/questions", tags=["questions"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _validate_question_values(options: list[str], correct_answer: str) -> None:
    if correct_answer not in options:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="correct_answer must be one of the options",
        )


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(payload: QuestionCreate, db: DatabaseSession) -> Question:
    if db.get(Topic, payload.topic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    question = Question(**payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("", response_model=list[QuestionRead])
def list_questions(
    db: DatabaseSession,
    subject_id: Optional[int] = Query(default=None),
    topic_id: Optional[int] = Query(default=None),
    difficulty: Optional[Difficulty] = Query(default=None),
) -> list[Question]:
    query = select(Question).join(Question.topic)
    if subject_id is not None:
        query = query.where(Topic.subject_id == subject_id)
    if topic_id is not None:
        query = query.where(Question.topic_id == topic_id)
    if difficulty is not None:
        query = query.where(Question.difficulty == difficulty)
    query = query.order_by(Question.id)
    return list(db.scalars(query).all())


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: int, db: DatabaseSession) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


@router.patch("/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: DatabaseSession,
) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    updates = payload.model_dump(exclude_unset=True)
    if "topic_id" in updates and db.get(Topic, updates["topic_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    options = updates.get("options", question.options)
    correct_answer = updates.get("correct_answer", question.correct_answer)
    _validate_question_values(options, correct_answer)

    for field, value in updates.items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: int, db: DatabaseSession) -> None:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    db.delete(question)
    db.commit()
