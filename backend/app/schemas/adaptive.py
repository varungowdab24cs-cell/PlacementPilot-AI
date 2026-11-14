from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MasteryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    topic_name: str
    mastery_score: Optional[float]
    mastery_level: str
    accuracy: Optional[float]
    consistency: Optional[float]
    practice_completion: Optional[float]
    assessment_count: int
    is_sufficient: bool
    updated_at: datetime


class OverallMasteryRead(BaseModel):
    overall_score: Optional[float]
    classified_topics: int
    total_topics: int
    sufficient_history: bool
    topics: list[MasteryRead]


class PracticeCreate(BaseModel):
    topic_id: int
    activity_type: str = Field(min_length=1, max_length=30)
    difficulty: str = Field(min_length=1, max_length=20)
    completed: bool = False
    questions_completed: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)
    learning_path_item_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_practice_counts(self) -> "PracticeCreate":
        if self.questions_completed > self.total_questions:
            raise ValueError("questions_completed cannot exceed total_questions")
        if self.completed and self.total_questions == 0:
            raise ValueError("A completed practice record must have questions")
        return self


class PracticeResponse(BaseModel):
    id: int
    topic_id: int
    completed: bool
    mastery: Optional[MasteryRead] = None


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    topic_name: str
    activity_type: str
    difficulty: str
    title: str
    rationale: str
    status: str
    created_at: datetime


class LearningPathItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    topic_name: str
    title: str
    activity_type: str
    difficulty: str
    rationale: str
    position: int
    status: str
    completed_at: Optional[datetime]


class LearningPathRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    completed_items: int
    total_items: int
    progress: float
    items: list[LearningPathItemRead]
