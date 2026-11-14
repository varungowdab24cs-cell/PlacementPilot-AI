from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.database import get_db
from backend.app.models import Student

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_student(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Student:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        student_id = decode_access_token(token)
    except InvalidTokenError:
        raise credentials_exception from None

    student = db.get(Student, student_id)
    if student is None:
        raise credentials_exception
    return student
