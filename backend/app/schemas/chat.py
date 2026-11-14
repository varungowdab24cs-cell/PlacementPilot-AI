from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TutorMode = Literal["concept", "hint", "aptitude", "programming"]


class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=150)


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    mode: TutorMode = "concept"
    topic_id: Optional[int] = None


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class TutorResponse(BaseModel):
    session_id: int
    user_message_id: int
    assistant_message_id: int
    answer: str
    suggested_actions: list[str]
    context_topic_ids: list[int]
    created_at: datetime
