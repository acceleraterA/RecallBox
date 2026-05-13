from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import settings


@dataclass
class LlmEnrichment:
    summary: Optional[str] = None
    tags: Optional[list[str]] = None


def generate_enrichment(*, title: Optional[str], description: Optional[str], note: Optional[str]) -> LlmEnrichment:
    if not settings.enable_llm or not settings.llm_api_key:
        return LlmEnrichment()

    # Provider intentionally stubbed for v1. The call site is wired so a future
    # provider can return generated summary/tags without changing API behavior.
    return LlmEnrichment()
