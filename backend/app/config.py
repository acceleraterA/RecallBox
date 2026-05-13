from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _database_url() -> str:
    value = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://recallbox:recallbox@localhost:5433/recallbox",
    )
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    return value


def _origins() -> list[str]:
    value = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=_database_url)
    frontend_origins: list[str] = field(default_factory=_origins)
    default_user_email: str = os.getenv("DEFAULT_USER_EMAIL", "demo@recallbox.local")
    enable_llm: bool = _env_bool("ENABLE_LLM", False)
    llm_api_key: Optional[str] = os.getenv("LLM_API_KEY")


settings = Settings()
