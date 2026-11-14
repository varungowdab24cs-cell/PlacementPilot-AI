from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.dependencies import get_current_student
from backend.app.database import get_db
from backend.app.models import ChatMessage, ChatSession, Student
from backend.app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionRead,
    TutorResponse,
)
from backend.app.services.chat_context import build_learning_context
from backend.app.services.groq_ai import (
    AIConfigurationError,
    AIProviderError,
    AIProviderRateLimitError,
    AIResponseError,
    get_groq_service,
)

router = APIRouter(prefix="/chat", tags=["tutoring"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentStudent = Annotated[Student, Depends(get_current_student)]


def _owned_session(db: Session, session_id: int, student_id: int) -> ChatSession:
    chat_session = db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.student_id == student_id,
        )
    )
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_session


@router.post(
    "/sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: ChatSessionCreate,
    student: CurrentStudent,
    db: DatabaseSession,
) -> ChatSession:
    chat_session = ChatSession(student_id=student.id, title=payload.title)
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_sessions(student: CurrentStudent, db: DatabaseSession) -> list[ChatSession]:
    return list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.student_id == student.id)
            .order_by(ChatSession.updated_at.desc())
        ).all()
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageRead],
)
def list_messages(
    session_id: int,
    student: CurrentStudent,
    db: DatabaseSession,
) -> list[ChatMessage]:
    _owned_session(db, session_id, student.id)
    return list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        ).all()
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=TutorResponse,
)
def send_message(
    session_id: int,
    payload: ChatMessageCreate,
    student: CurrentStudent,
    db: DatabaseSession,
) -> TutorResponse:
    chat_session = _owned_session(db, session_id, student.id)
    history = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        ).all()
    )
    user_message = ChatMessage(
        session_id=session_id,
        role="user",
        content=payload.message,
    )
    db.add(user_message)
    db.flush()
    context = build_learning_context(db, student.id, payload.topic_id)
    try:
        completion = get_groq_service().generate_tutor_response(
            student_id=student.id,
            mode=payload.mode,
            message=payload.message,
            context=context,
            history=[{"role": item.role, "content": item.content} for item in history],
        )
    except AIProviderRateLimitError as exc:
        db.rollback()
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds is not None
            else None
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI request rate limit exceeded",
            headers=headers,
        ) from exc
    except AIConfigurationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI tutoring is not configured",
        ) from exc
    except AIResponseError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an invalid response",
        ) from exc
    except AIProviderError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI tutoring provider is unavailable",
        ) from exc

    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=completion.answer,
    )
    db.add(assistant_message)
    chat_session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return TutorResponse(
        session_id=session_id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        answer=completion.answer,
        suggested_actions=completion.suggested_actions,
        context_topic_ids=[item["topic_id"] for item in context],
        created_at=assistant_message.created_at,
    )
