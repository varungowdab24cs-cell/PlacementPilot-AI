from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.database import get_db
from backend.app.models import Student
from backend.app.schemas.auth import LoginRequest, StudentRegistration, TokenResponse
from backend.app.schemas.students import StudentProfileRead

router = APIRouter(prefix="/auth", tags=["authentication"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=StudentProfileRead,
    status_code=status.HTTP_201_CREATED,
)
def register_student(payload: StudentRegistration, db: DatabaseSession) -> Student:
    email = str(payload.email).lower()
    existing_student = db.scalar(
        select(Student).where(func.lower(Student.email) == email)
    )
    if existing_student is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this email already exists",
        )

    student = Student(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        department=payload.department,
        semester=payload.semester,
        programming_language_preference=payload.programming_language_preference,
        target_company_categories=payload.target_company_categories,
        preparation_goals=payload.preparation_goals,
    )
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this email already exists",
        ) from None
    db.refresh(student)
    return student


@router.post("/login", response_model=TokenResponse)
def login_student(payload: LoginRequest, db: DatabaseSession) -> TokenResponse:
    email = str(payload.email).lower()
    student = db.scalar(select(Student).where(func.lower(Student.email) == email))
    if student is None or not verify_password(payload.password, student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(student.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )
