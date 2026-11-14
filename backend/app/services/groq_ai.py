import json
import logging
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from groq import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    Groq,
    RateLimitError,
)
from pydantic import ValidationError

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.ai import TutorCompletion
from backend.app.services.rate_limit import ai_rate_limiter

logger = logging.getLogger(__name__)


class AIConfigurationError(Exception):
    pass


class AIProviderError(Exception):
    pass


class AIProviderRateLimitError(AIProviderError):
    def __init__(self, retry_after_seconds: int | None = None) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("The AI provider rate limit was exceeded")


class AIResponseError(AIProviderError):
    pass


class GroqAIService:
    def __init__(self, client: Any | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if client is None:
            if not self.settings.groq_api_key or not self.settings.groq_model:
                raise AIConfigurationError(
                    "GROQ_API_KEY and GROQ_MODEL must be configured"
                )
            client = Groq(
                api_key=self.settings.groq_api_key,
                timeout=self.settings.groq_timeout_seconds,
                max_retries=0,
            )
        self.client = client

    def generate_tutor_response(
        self,
        *,
        student_id: int,
        mode: str,
        message: str,
        context: Sequence[dict[str, Any]],
        history: Sequence[dict[str, str]],
    ) -> TutorCompletion:
        ai_rate_limiter.check(
            str(student_id),
            self.settings.ai_rate_limit_per_minute,
        )
        messages = self._build_messages(mode, message, context, history)
        try:
            completion = self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
        except RateLimitError as exc:
            raise AIProviderRateLimitError(
                getattr(exc, "response", None)
                and getattr(exc.response, "headers", {}).get("retry-after")
            ) from exc
        except APITimeoutError as exc:
            logger.warning("Groq request timed out")
            raise AIProviderError("The AI provider timed out") from exc
        except APIConnectionError as exc:
            logger.warning("Groq connection failed")
            raise AIProviderError("The AI provider could not be reached") from exc
        except APIStatusError as exc:
            if exc.status_code == 429:
                raise AIProviderRateLimitError() from exc
            logger.warning("Groq returned an HTTP error status")
            raise AIProviderError("The AI provider returned an error") from exc
        except APIError as exc:
            logger.warning("Groq returned an API error")
            raise AIProviderError("The AI provider returned an error") from exc

        content = completion.choices[0].message.content
        if not content:
            raise AIResponseError("The AI provider returned an empty response")
        try:
            return TutorCompletion.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise AIResponseError("The AI provider returned an invalid response") from exc

    def _build_messages(
        self,
        mode: str,
        message: str,
        context: Sequence[dict[str, Any]],
        history: Sequence[dict[str, str]],
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are PlacementPilot AI, a precise placement-preparation tutor. "
            f"Answer in {mode} mode. Use only the supplied student learning context "
            "when making personalization claims. Explain reasoning clearly, ask "
            "a concise follow-up question when context is insufficient, and never "
            "invent mastery data. Return only valid JSON with keys 'answer' and "
            "'suggested_actions' (an array of at most five short strings). "
            "The Python backend is the sole authority for assessment scores and "
            "mastery calculations; never calculate, modify, or claim official scores."
            f"\nStudent learning context: {json.dumps(list(context), separators=(',', ':'))}"
        )
        bounded_history = list(history)[-self.settings.ai_max_history_messages :]
        return [
            {"role": "system", "content": system_prompt},
            *bounded_history,
            {"role": "user", "content": message},
        ]


@lru_cache(maxsize=1)
def get_groq_service() -> GroqAIService:
    return GroqAIService()
