from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Difficulty = Literal["easy", "medium", "hard"]


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None


class SubjectRead(SubjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None


class TopicCreate(BaseModel):
    subject_id: int
    prerequisite_topic_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None


class TopicRead(TopicCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class TopicUpdate(BaseModel):
    prerequisite_topic_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None


class QuestionCreate(BaseModel):
    topic_id: int
    prompt: str = Field(min_length=1)
    question_type: Literal["mcq"] = "mcq"
    difficulty: Difficulty
    options: list[str] = Field(min_length=2, max_length=10)
    correct_answer: str = Field(min_length=1, max_length=500)
    explanation: Optional[str] = None
    estimated_solving_time_seconds: int = Field(gt=0, le=3600)
    is_sample: bool = False

    @model_validator(mode="after")
    def validate_correct_answer(self) -> "QuestionCreate":
        if self.correct_answer not in self.options:
            raise ValueError("correct_answer must be one of the options")
        return self


class QuestionUpdate(BaseModel):
    topic_id: Optional[int] = None
    prompt: Optional[str] = Field(default=None, min_length=1)
    question_type: Optional[Literal["mcq"]] = None
    difficulty: Optional[Difficulty] = None
    options: Optional[list[str]] = Field(default=None, min_length=2, max_length=10)
    correct_answer: Optional[str] = Field(default=None, min_length=1, max_length=500)
    explanation: Optional[str] = None
    estimated_solving_time_seconds: Optional[int] = Field(default=None, gt=0, le=3600)
    is_sample: Optional[bool] = None


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    prompt: str
    question_type: Literal["mcq"]
    difficulty: Difficulty
    options: list[str]
    estimated_solving_time_seconds: int
    is_sample: bool
    created_at: datetime
    updated_at: datetime


class AssessmentCreate(BaseModel):
    subject_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    question_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_questions(self) -> "AssessmentCreate":
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError("question_ids must be unique")
        return self


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: Optional[int]
    title: str
    description: Optional[str]
    question_count: int
    created_at: datetime
    updated_at: datetime


class AssessmentQuestion(BaseModel):
    id: int
    topic_id: int
    prompt: str
    question_type: Literal["mcq"]
    difficulty: Difficulty
    options: list[str]
    estimated_solving_time_seconds: int


class AssessmentStartResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    started_at: datetime
    questions: list[AssessmentQuestion]


class SubmittedAnswer(BaseModel):
    question_id: int
    selected_answer: str = Field(min_length=1, max_length=500)
    time_taken_seconds: int = Field(ge=0, le=86400)


class AssessmentSubmission(BaseModel):
    answers: list[SubmittedAnswer] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_answers(self) -> "AssessmentSubmission":
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each question may be answered only once")
        return self


class AnswerResult(BaseModel):
    question_id: int
    selected_answer: str
    correct_answer: str
    explanation: Optional[str]
    is_correct: bool
    time_taken_seconds: int


class TopicPerformance(BaseModel):
    topic_id: int
    topic_name: str
    total_questions: int
    answered_questions: int
    correct_answers: int
    score: float


class AssessmentResult(BaseModel):
    attempt_id: int
    assessment_id: int
    score: float
    total_questions: int
    answered_questions: int
    completed_at: datetime
    answers: list[AnswerResult]
    topic_performance: list[TopicPerformance]


class AssessmentHistoryRead(BaseModel):
    attempt_id: int
    assessment_id: int
    assessment_title: str
    score: Optional[float]
    answered_questions: int
    completed_at: datetime
