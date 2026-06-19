from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Optional

from huggingface_hub import InferenceClient
import requests

from app.config import settings
from app.models import Item

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingResult:
    values: list[float]
    provider: str
    model: str

    @property
    def dimensions(self) -> int:
        return len(self.values)


def build_item_embedding_text(item: Item, tag_names: list[str]) -> str:
    parts = [
        ("title", item.title),
        ("description", item.description),
        ("summary", item.summary),
        ("note", item.note),
        ("platform", item.platform),
        ("tags", ", ".join(sorted(tag_names))),
        ("url", item.url),
    ]
    text = "\n".join(f"{label}: {value.strip()}" for label, value in parts if value and value.strip())
    return text[:12000]


def format_vector(values: list[float]) -> str:
    return json.dumps(values, separators=(",", ":"))


def _normalize_vector(value: object) -> Optional[list[float]]:
    if hasattr(value, "tolist"):
        value = value.tolist()

    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]

    if not isinstance(value, list) or not value or isinstance(value[0], list):
        return None

    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def _generate_huggingface_embedding(text: str, *, is_query: bool = False) -> Optional[EmbeddingResult]:
    if not settings.huggingface_token:
        logger.warning("HUGGINGFACE_TOKEN is required for the huggingface embedding provider")
        return None

    if is_query and settings.huggingface_embedding_model.startswith("BAAI/bge-"):
        text = "Represent this sentence for searching relevant passages: " + text

    try:
        client = InferenceClient(provider="hf-inference", api_key=settings.huggingface_token)
        response = client.feature_extraction(
            text,
            model=settings.huggingface_embedding_model,
            normalize=True,
        )
    except Exception as exc:
        logger.warning("Hugging Face embedding request failed: %s", exc)
        return None

    values = _normalize_vector(response)
    if not values:
        logger.warning("Hugging Face embedding response was not a one-dimensional vector")
        return None

    return EmbeddingResult(
        values=values,
        provider="huggingface",
        model=settings.huggingface_embedding_model,
    )


def _generate_openai_embedding(text: str, *, is_query: bool = False) -> Optional[EmbeddingResult]:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is required for the openai embedding provider")
        return None

    payload: dict[str, object] = {
        "model": settings.openai_embedding_model,
        "input": text,
        "encoding_format": "float",
    }
    if settings.openai_embedding_dimensions:
        payload["dimensions"] = settings.openai_embedding_dimensions

    try:
        response = requests.post(
            OPENAI_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        values = _normalize_vector(data["data"][0]["embedding"])
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        body = exc.response.text[:500] if exc.response is not None else ""
        logger.warning("OpenAI embedding request failed with status %s: %s", status_code, body)
        return None
    except requests.RequestException as exc:
        logger.warning("OpenAI embedding request failed: %s", exc)
        return None
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("OpenAI embedding response could not be parsed: %s", exc)
        return None

    if not values:
        return None

    return EmbeddingResult(
        values=values,
        provider="openai",
        model=settings.openai_embedding_model,
    )


def generate_embedding(text: str, *, is_query: bool = False) -> Optional[EmbeddingResult]:
    if not settings.enable_embeddings or not text.strip():
        return None

    providers = {
        "huggingface": _generate_huggingface_embedding,
        "openai": _generate_openai_embedding,
    }
    provider = providers.get(settings.embedding_provider)
    if not provider:
        logger.warning("Unsupported embedding provider: %s", settings.embedding_provider)
        return None
    return provider(text, is_query=is_query)
