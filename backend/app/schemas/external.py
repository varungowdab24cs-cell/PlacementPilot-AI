from datetime import datetime
from typing import Literal, Optional

from pydantic import AnyHttpUrl, BaseModel, Field

ExternalPlatform = Literal["leetcode", "codeforces"]
ProblemDifficulty = Literal["easy", "medium", "hard"]
ProblemOutcome = Literal["attempted", "solved", "need_help", "skipped"]


class ExternalProblemRead(BaseModel):
    id: int
    title: str
    platform: ExternalPlatform
    topic_id: int
    topic_name: str
    difficulty: ProblemDifficulty
    official_url: AnyHttpUrl
    description: Optional[str]
    prerequisite_topic_ids: list[int]
    recommended_company_categories: list[str]


class ExternalProblemAttemptCreate(BaseModel):
    outcome: ProblemOutcome
    solving_time_seconds: Optional[int] = Field(default=None, ge=0)


class ExternalProblemAttemptRead(BaseModel):
    id: int
    resource_id: int
    topic_id: int
    outcome: ProblemOutcome
    solving_time_seconds: Optional[int]
    completion_source: Literal["self_reported", "verified"]
    verified: bool
    created_at: datetime


class ExternalPracticeStatsRead(BaseModel):
    attempted: int
    solved: int
    need_help: int
    skipped: int
    average_solving_time_seconds: Optional[float]
    self_reported_count: int
    verified_count: int


