from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ExperimentCondition = Literal["control", "experimental"]
AssessmentPhase = Literal["pre", "post"]


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    control_topic_ids: list[int] = Field(default_factory=list)


class ExperimentRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    starts_at: datetime
    ends_at: Optional[datetime]
    control_topic_ids: list[int]


class ExperimentAssignmentRead(BaseModel):
    experiment_id: int
    condition: ExperimentCondition
    assigned_at: datetime


class ExperimentSequenceRead(BaseModel):
    experiment_id: int
    condition: ExperimentCondition
    sequence_type: Literal["fixed", "adaptive"]
    topic_ids: list[int]


class AssessmentAnalyticsRead(BaseModel):
    attempt_id: int
    assessment_id: int
    assessment_title: str
    phase: Optional[AssessmentPhase]
    score: Optional[float]
    answered_questions: int
    total_questions: int
    completion_rate: Optional[float]
    average_time_taken_seconds: Optional[float]
    completed_at: datetime


class TopicMasteryTimelineRead(BaseModel):
    topic_id: int
    topic_name: str
    score: Optional[float]
    is_sufficient: bool
    assessment_count: int
    recorded_at: datetime


class StudentAnalyticsRead(BaseModel):
    pre_test_score: Optional[float]
    post_test_score: Optional[float]
    assessment_history: list[AssessmentAnalyticsRead]
    topic_mastery_history: list[TopicMasteryTimelineRead]
    dsa_practice: dict[str, int | float | None]


class StatisticalSummary(BaseModel):
    n: int
    mean: Optional[float]
    standard_deviation: Optional[float]
    confidence_interval_low: Optional[float]
    confidence_interval_high: Optional[float]


class ResearchGroupAggregate(BaseModel):
    condition: ExperimentCondition
    participant_count: int
    pre_test: StatisticalSummary
    post_test: StatisticalSummary
    improvement: StatisticalSummary
    assessment_completion: StatisticalSummary
    dsa_solved: StatisticalSummary
    topic_mastery_change: StatisticalSummary


class ResearchComparison(BaseModel):
    metric: str
    control_n: int
    experimental_n: int
    statistic: Optional[float]
    p_value: Optional[float]


class ResearchAggregateReport(BaseModel):
    experiment_id: int
    experiment_name: str
    evaluation_start: datetime
    evaluation_end: Optional[datetime]
    generated_at: datetime
    groups: list[ResearchGroupAggregate]
    comparisons: list[ResearchComparison]
