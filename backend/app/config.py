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


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        return default


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
    enable_auth: bool = _env_bool("ENABLE_AUTH", False)
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_anon_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
    enable_llm: bool = _env_bool("ENABLE_LLM", False)
    llm_api_key: Optional[str] = os.getenv("LLM_API_KEY")
    enable_embeddings: bool = _env_bool("ENABLE_EMBEDDINGS", False)
    embedding_min_similarity: float = _env_float("EMBEDDING_MIN_SIMILARITY", 0.55)
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "huggingface").strip().lower()
    huggingface_token: Optional[str] = os.getenv("HUGGINGFACE_TOKEN")
    huggingface_embedding_model: str = os.getenv(
        "HUGGINGFACE_EMBEDDING_MODEL",
        "BAAI/bge-small-en-v1.5",
    )
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_embedding_dimensions: int = _env_int("OPENAI_EMBEDDING_DIMENSIONS", 1536)


settings = Settings()
