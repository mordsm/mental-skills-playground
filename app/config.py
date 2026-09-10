from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MSP_", env_file=".env", extra="ignore")

    actions_api_key: str = Field(default="dev-only-change-me")
    database_path: Path = Field(default=Path("data/mental-skills-playground.db"))
    public_base_url: str = Field(default="http://localhost:8010")
    user_id: str = Field(default="moshe")


@lru_cache
def get_settings() -> Settings:
    return Settings()

