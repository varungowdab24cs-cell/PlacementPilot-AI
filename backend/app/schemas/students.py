from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_categories(categories: list[str]) -> list[str]:
    cleaned = [category.strip() for category in categories]
    if any(not category for category in cleaned):
        raise ValueError("Target company categories cannot be empty")
    return cleaned


class StudentProfileFields(BaseModel):
    department: Optional[str] = Field(default=None, max_length=120)
    semester: Optional[int] = Field(default=None, ge=1, le=20)
    programming_language_preference: Optional[str] = Field(default=None, max_length=80)
    target_company_categories: list[str] = Field(default_factory=list, max_length=20)
    preparation_goals: Optional[str] = None

    @field_validator("target_company_categories")
    @classmethod
    def validate_categories(cls, value: list[str]) -> list[str]:
        return _clean_categories(value)


class StudentProfileUpdate(StudentProfileFields):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            raise ValueError("Full name cannot be null")
        if not value.strip():
            raise ValueError("Full name cannot be empty")
        return value


class StudentProfileRead(StudentProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    created_at: datetime
    updated_at: datetime
