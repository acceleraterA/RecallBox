from __future__ import annotations

from datetime import datetime
from typing import Optional

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
    note: Optional[str] = Field(default=None, max_length=5000)
    tags: Optional[list[str]] = None


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
    status: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
