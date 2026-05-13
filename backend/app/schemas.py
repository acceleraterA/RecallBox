from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ItemCreate(BaseModel):
    url: HttpUrl
    note: Optional[str] = Field(default=None, max_length=5000)


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
