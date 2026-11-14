from pydantic import BaseModel, Field


class TutorCompletion(BaseModel):
    answer: str = Field(min_length=1)
    suggested_actions: list[str] = Field(default_factory=list, max_length=5)
