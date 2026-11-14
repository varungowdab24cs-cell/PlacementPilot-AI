from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_student
from backend.app.database import get_db
from backend.app.models import Student
from backend.app.schemas.students import StudentProfileRead, StudentProfileUpdate

router = APIRouter(prefix="/students", tags=["students"])
CurrentStudent = Annotated[Student, Depends(get_current_student)]
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/me", response_model=StudentProfileRead)
def read_current_student(student: CurrentStudent) -> Student:
    return student


@router.patch("/me", response_model=StudentProfileRead)
def update_current_student(
    payload: StudentProfileUpdate,
    student: CurrentStudent,
    db: DatabaseSession,
) -> Student:
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "full_name" and value is not None:
            value = value.strip()
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    return student
