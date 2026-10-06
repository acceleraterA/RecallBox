from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Optional

from huggingface_hub import InferenceClient
import requests

from app.config import settings
from app.rag import RetrievedChunk

logger = logging.getLogger(__name__)
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


@dataclass
class LlmEnrichment:
    summary: Optional[str] = None
    tags: Optional[list[str]] = None


@dataclass(frozen=True)
class RagAnswerResult:
    answer: str
    mode: str
    model: Optional[str] = None


def generate_enrichment(
    *,
    title: Optional[str],
    description: Optional[str],
    note: Optional[str],
) -> LlmEnrichment:
    # V2 focuses LLM usage on grounded Q&A. Metadata enrichment remains optional.
    return LlmEnrichment()


def _ensure_source_marker(answer: str) -> str:
    if re.search(r"\[\d+\]", answer):
        return answer
    return answer + "\n\nSources: [1]"


def _source_context(chunks: list[RetrievedChunk]) -> str:
    sources = []
    for index, chunk in enumerate(chunks, start=1):
        sources.append(
            f"[{index}] {chunk.title}\n"
            f"URL: {chunk.url}\n"
            f"Passage: {chunk.content}"
        )
    return "\n\n".join(sources)


def _messages(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    system = (
        "You are RecallBox, a grounded research assistant. Answer only from the supplied "
        "saved-link passages. Cite factual claims using source markers like [1] or [2]. "
        "If the passages do not contain enough information, say that clearly. Never invent "
        "a source, URL, or fact."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.extend(history[-6:])
    messages.append(
        {
            "role": "user",
            "content": (
                f"Saved-link passages:\n\n{_source_context(chunks)}\n\n"
                f"Question: {question}\n\n"
                "Give a concise answer with inline citations."
            ),
        }
    )
    return messages


def _huggingface_answer(messages: list[dict[str, str]]) -> Optional[RagAnswerResult]:
    if not settings.huggingface_token:
        logger.warning("HUGGINGFACE_TOKEN is required for Hugging Face RAG answers")
        return None
    try:
        client = InferenceClient(provider="auto", api_key=settings.huggingface_token)
        extra_body = (
            {"reasoning_effort": "low"}
            if settings.huggingface_chat_model.startswith("openai/gpt-oss-")
            else None
        )
        response = client.chat_completion(
            messages,
            model=settings.huggingface_chat_model,
            max_tokens=settings.rag_max_answer_tokens,
            temperature=0.2,
            extra_body=extra_body,
        )
        content = response.choices[0].message.content
    except Exception as exc:
        logger.warning("Hugging Face RAG answer failed: %s", exc)
        return None

    if not isinstance(content, str) or not content.strip():
        return None
    answer = _ensure_source_marker(content.strip())
    return RagAnswerResult(
        answer=answer,
        mode="llm",
        model=settings.huggingface_chat_model,
    )


def _openai_answer(messages: list[dict[str, str]]) -> Optional[RagAnswerResult]:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is required for OpenAI RAG answers")
        return None
    try:
        response = requests.post(
            OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_chat_model,
                "messages": messages,
                "max_tokens": settings.rag_max_answer_tokens,
                "temperature": 0.2,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("OpenAI RAG answer failed: %s", exc)
        return None

    if not isinstance(content, str) or not content.strip():
        return None
    return RagAnswerResult(
        answer=_ensure_source_marker(content.strip()),
        mode="llm",
        model=settings.openai_chat_model,
    )


def _retrieval_fallback(chunks: list[RetrievedChunk]) -> RagAnswerResult:
    if not chunks:
        return RagAnswerResult(
            answer=(
                "I could not find a sufficiently relevant passage in your saved links. "
                "Try a more specific question or save a source that covers this topic."
            ),
            mode="no_context",
        )

    lines = [
        "The answer model is unavailable, but I found these relevant saved passages:"
    ]
    for index, chunk in enumerate(chunks[:3], start=1):
        excerpt = " ".join(chunk.content.split())[:320]
        lines.append(f"[{index}] {excerpt}")
    return RagAnswerResult(answer="\n\n".join(lines), mode="retrieval_only")


def generate_rag_answer(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
) -> RagAnswerResult:
    if not chunks:
        return _retrieval_fallback(chunks)
    if not settings.enable_llm:
        return _retrieval_fallback(chunks)

    messages = _messages(question=question, chunks=chunks, history=history)
    providers = {
        "huggingface": _huggingface_answer,
        "openai": _openai_answer,
    }
    provider = providers.get(settings.llm_provider)
    if not provider:
        logger.warning("Unsupported LLM provider: %s", settings.llm_provider)
        return _retrieval_fallback(chunks)
    return provider(messages) or _retrieval_fallback(chunks)
