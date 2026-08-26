from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from the environment and local .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str | None = None
    test_database_url: str | None = None
    backend_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:8000")
    frontend_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:5173")
    cors_origins: list[AnyHttpUrl] = [AnyHttpUrl("http://127.0.0.1:5173")]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
