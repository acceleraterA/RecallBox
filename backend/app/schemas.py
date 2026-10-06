from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.share import extract_first_url


class ItemCreate(BaseModel):
    url: str = Field(..., max_length=10000)
    note: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("url")
    @classmethod
    def must_contain_url(cls, value: str) -> str:
        if not extract_first_url(value):
            raise ValueError("Paste a valid URL or share text containing a URL")
        return value


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    note: Optional[str] = Field(default=None, max_length=5000)
    thumbnail_url: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[list[str]] = None

    @field_validator("title")
    @classmethod
    def title_must_be_clean_or_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = " ".join(value.strip().split())
        return cleaned or None

    @field_validator("thumbnail_url")
    @classmethod
    def thumbnail_must_be_url_or_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("Thumbnail URL must start with http:// or https://")
        return cleaned


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    platform: str
    title: Optional[str]
    description: Optional[str]
    summary: Optional[str]
    note: Optional[str]
    thumbnail_url: Optional[str]
    content_status: str
    status: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

class RagHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class RagAskInput(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    history: list[RagHistoryMessage] = Field(default_factory=list, max_length=6)
    top_k: Optional[int] = Field(default=None, ge=1, le=8)


class RagCitationOut(BaseModel):
    item_id: int
    title: str
    url: str
    excerpt: str
    chunk_index: int
    similarity: float


class RagAnswerOut(BaseModel):
    answer: str
    citations: list[RagCitationOut]
    mode: Literal["llm", "retrieval_only", "no_context"]
    model: Optional[str] = None
