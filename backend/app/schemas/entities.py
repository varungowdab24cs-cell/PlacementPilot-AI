from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.app.schemas.common import TimestampedRead


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=255)


class StudentRead(StudentCreate, TimestampedRead):
    pass


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None


class SubjectRead(SubjectCreate, TimestampedRead):
    pass


class TopicCreate(BaseModel):
    subject_id: int
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None


class TopicRead(TopicCreate, TimestampedRead):
    pass


class QuestionCreate(BaseModel):
    topic_id: int
    prompt: str = Field(min_length=1)
    question_type: str = Field(min_length=1, max_length=30)
    difficulty: str = Field(min_length=1, max_length=20)
    explanation: Optional[str] = None


class QuestionRead(QuestionCreate, TimestampedRead):
    pass


class AssessmentCreate(BaseModel):
    subject_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    question_ids: list[int] = Field(default_factory=list)


class AssessmentRead(AssessmentCreate, TimestampedRead):
    pass


class AssessmentAttemptCreate(BaseModel):
    assessment_id: int
    student_id: int
    started_at: datetime


class AssessmentAttemptRead(AssessmentAttemptCreate, TimestampedRead):
    score: Optional[float] = None
    completed_at: Optional[datetime] = None


class StudentAnswerCreate(BaseModel):
    attempt_id: int
    student_id: int
    question_id: int
    answer_text: str = Field(min_length=1)
    is_correct: Optional[bool] = None
    answered_at: datetime


class StudentAnswerRead(StudentAnswerCreate, TimestampedRead):
    pass


class TopicMasteryCreate(BaseModel):
    student_id: int
    topic_id: int
    mastery_score: float = Field(default=0, ge=0, le=100)


class TopicMasteryRead(TopicMasteryCreate, TimestampedRead):
    pass


class LearningPathCreate(BaseModel):
    student_id: int
    title: str = Field(min_length=1, max_length=150)
    status: str = Field(default="active", min_length=1, max_length=30)


class LearningPathRead(LearningPathCreate, TimestampedRead):
    pass


class ResourceCreate(BaseModel):
    topic_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=150)
    resource_type: str = Field(min_length=1, max_length=30)
    url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None


class ResourceRead(ResourceCreate, TimestampedRead):
    pass


class ChatSessionCreate(BaseModel):
    student_id: int
    title: Optional[str] = Field(default=None, max_length=150)


class ChatSessionRead(ChatSessionCreate, TimestampedRead):
    pass


class ChatMessageCreate(BaseModel):
    session_id: int
    role: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=1)


class ChatMessageRead(ChatMessageCreate, TimestampedRead):
    pass


__all__ = [
    "AssessmentAttemptCreate",
    "AssessmentAttemptRead",
    "AssessmentCreate",
    "AssessmentRead",
    "ChatMessageCreate",
    "ChatMessageRead",
    "ChatSessionCreate",
    "ChatSessionRead",
    "LearningPathCreate",
    "LearningPathRead",
    "QuestionCreate",
    "QuestionRead",
    "ResourceCreate",
    "ResourceRead",
    "StudentAnswerCreate",
    "StudentAnswerRead",
    "StudentCreate",
    "StudentRead",
    "SubjectCreate",
    "SubjectRead",
    "TopicCreate",
    "TopicMasteryCreate",
    "TopicMasteryRead",
    "TopicRead",
]
