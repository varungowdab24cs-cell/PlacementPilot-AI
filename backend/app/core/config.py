from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PlacementPilot AI"
    debug: bool = False
    database_url: str = "sqlite:///./placementpilot.db"
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    mastery_accuracy_weight: float = 0.6
    mastery_consistency_weight: float = 0.2
    mastery_practice_weight: float = 0.2
    mastery_minimum_assessment_attempts: int = 2
    mastery_weak_threshold: float = 40
    mastery_developing_threshold: float = 60
    mastery_good_threshold: float = 80
    groq_api_key: str = ""
    groq_model: str = ""
    groq_timeout_seconds: float = 30
    ai_rate_limit_per_minute: int = 20
    ai_max_history_messages: int = 12
    ai_max_context_topics: int = 5
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    researcher_api_key: str = ""
    cors_origins: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
