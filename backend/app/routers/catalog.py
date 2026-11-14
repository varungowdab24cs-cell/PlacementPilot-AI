from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Subject, Topic
from backend.app.schemas.assessment import (
    SubjectCreate,
    SubjectRead,
    SubjectUpdate,
    TopicCreate,
    TopicRead,
    TopicUpdate,
)

router = APIRouter(tags=["catalog"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreate, db: DatabaseSession) -> Subject:
    subject = Subject(name=payload.name.strip(), description=payload.description)
    db.add(subject)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subject with this name already exists",
        ) from None
    db.refresh(subject)
    return subject


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(db: DatabaseSession) -> list[Subject]:
    return list(db.scalars(select(Subject).order_by(Subject.name)).all())


@router.get("/subjects/{subject_id}", response_model=SubjectRead)
def get_subject(subject_id: int, db: DatabaseSession) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject


@router.patch("/subjects/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: DatabaseSession,
) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(subject, field, value.strip() if field == "name" else value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subject with this name already exists",
        ) from None
    db.refresh(subject)
    return subject


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, db: DatabaseSession) -> None:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    db.delete(subject)
    db.commit()


@router.post("/topics", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
def create_topic(payload: TopicCreate, db: DatabaseSession) -> Topic:
    subject = db.get(Subject, payload.subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if payload.prerequisite_topic_id is not None:
        prerequisite = db.get(Topic, payload.prerequisite_topic_id)
        if prerequisite is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prerequisite topic not found",
            )
    topic = Topic(
        subject_id=payload.subject_id,
        prerequisite_topic_id=payload.prerequisite_topic_id,
        name=payload.name.strip(),
        description=payload.description,
    )
    db.add(topic)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A topic with this name already exists for the subject",
        ) from None
    db.refresh(topic)
    return topic


@router.get("/topics", response_model=list[TopicRead])
def list_topics(
    db: DatabaseSession,
    subject_id: Optional[int] = Query(default=None),
) -> list[Topic]:
    query = select(Topic).order_by(Topic.name)
    if subject_id is not None:
        query = query.where(Topic.subject_id == subject_id)
    return list(db.scalars(query).all())


@router.get("/topics/{topic_id}", response_model=TopicRead)
def get_topic(topic_id: int, db: DatabaseSession) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    if (
        "prerequisite_topic_id" in payload.model_fields_set
        and payload.prerequisite_topic_id == topic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A topic cannot be its own prerequisite",
        )
    if payload.prerequisite_topic_id is not None and db.get(
        Topic, payload.prerequisite_topic_id
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prerequisite topic not found",
        )
    return topic


@router.patch("/topics/{topic_id}", response_model=TopicRead)
def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    db: DatabaseSession,
) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(topic, field, value.strip() if field == "name" else value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A topic with this name already exists for the subject",
        ) from None
    db.refresh(topic)
    return topic


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: int, db: DatabaseSession) -> None:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    db.delete(topic)
    db.commit()
