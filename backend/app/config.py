from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    groq_api_key: str
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Llama proved more reliable for names, titles and motive prose.
    # Python owns all evidence logic, so JSON Object Mode is sufficient.
    groq_model: str = "llama-3.3-70b-versatile"
    generation_reasoning_effort: str = "low"
    generation_max_retries: int = 3
    generation_temperature: float = 0.25
    narrative_max_tokens: int = 1_200
    request_timeout_seconds: float = 45.0

    # Kept for compatibility with existing .env files and diagnostics.
    core_max_tokens: int = 1_200
    suspect_max_tokens: int = 1_300
    evidence_max_tokens: int = 2_200
    review_max_tokens: int = 650

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
