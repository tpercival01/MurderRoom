from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    groq_api_key: str
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"

    generation_max_retries: int = 3
    generation_temperature: float = 0.4

    core_max_tokens: int = 900
    suspect_max_tokens: int = 1_300
    evidence_max_tokens: int = 2_200
    review_max_tokens: int = 650

    generation_reasoning_effort: str = "low"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
