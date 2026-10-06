from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.embeddings import EmbeddingResult, format_vector, generate_embedding
from app.models import Item, ItemChunk


@dataclass(frozen=True)
class RetrievedChunk:
    item_id: int
    title: str
    url: str
    chunk_index: int
    content: str
    similarity: float


def _normalize_content(value: str) -> str:
    paragraphs = [" ".join(part.split()) for part in value.splitlines()]
    return "\n\n".join(part for part in paragraphs if part)


def build_rag_document(item: Item) -> str:
    sections = [
        f"Title: {item.title}" if item.title else None,
        f"Description: {item.description}" if item.description else None,
        f"Note: {item.note}" if item.note else None,
        f"Tags: {', '.join(sorted(tag.name for tag in item.tags))}" if item.tags else None,
        item.content_text,
    ]
    document = "\n\n".join(section.strip() for section in sections if section and section.strip())
    return _normalize_content(document)[: settings.rag_max_content_chars]


def chunk_document(document: str) -> list[str]:
    if not document:
        return []

    chunk_size = max(settings.rag_chunk_size, 400)
    overlap = min(max(settings.rag_chunk_overlap, 0), chunk_size // 2)
    max_chunks = max(settings.rag_max_chunks_per_item, 1)
    chunks: list[str] = []
    start = 0

    while start < len(document) and len(chunks) < max_chunks:
        hard_end = min(start + chunk_size, len(document))
        end = hard_end
        if hard_end < len(document):
            minimum_boundary = start + int(chunk_size * 0.6)
            paragraph_boundary = document.rfind("\n\n", minimum_boundary, hard_end)
            word_boundary = document.rfind(" ", minimum_boundary, hard_end)
            end = max(paragraph_boundary, word_boundary)
            if end <= start:
                end = hard_end

        chunk = document[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(document):
            break
        next_start = max(end - overlap, start + 1)
        if next_start > 0 and not document[next_start - 1].isspace():
            boundary = document.find(" ", next_start, min(end, next_start + 80))
            if boundary != -1:
                next_start = boundary + 1
        start = next_start

    return chunks


def has_chunk_embedding_storage(db: Session) -> bool:
    return bool(
        db.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'item_chunks' AND column_name = 'embedding'
                )
                """
            )
        )
    )


def _store_chunk_embedding(
    db: Session,
    *,
    chunk: ItemChunk,
    embedding: EmbeddingResult,
) -> None:
    if not has_chunk_embedding_storage(db):
        return
    db.execute(
        text(
            """
            UPDATE item_chunks
            SET embedding = CAST(:embedding AS vector),
                embedding_provider = :provider,
                embedding_model = :model,
                embedding_dimensions = :dimensions
            WHERE id = :chunk_id
            """
        ),
        {
            "chunk_id": chunk.id,
            "embedding": format_vector(embedding.values),
            "provider": embedding.provider,
            "model": embedding.model,
            "dimensions": embedding.dimensions,
        },
    )
    chunk.embedding_provider = embedding.provider
    chunk.embedding_model = embedding.model
    chunk.embedding_dimensions = embedding.dimensions


def index_item_content(db: Session, item: Item) -> int:
    db.execute(delete(ItemChunk).where(ItemChunk.item_id == item.id))
    db.flush()

    document = build_rag_document(item)
    chunks = chunk_document(document)
    if not chunks:
        item.content_status = "failed"
        return 0

    embedded_count = 0
    for index, content in enumerate(chunks):
        chunk = ItemChunk(
            item_id=item.id,
            user_id=item.user_id,
            chunk_index=index,
            content=content,
        )
        db.add(chunk)
        db.flush()
        embedding = generate_embedding(content)
        if embedding:
            _store_chunk_embedding(db, chunk=chunk, embedding=embedding)
            embedded_count += 1

    item.content_status = "ready" if embedded_count else "partial"
    return embedded_count


def retrieve_chunks(
    db: Session,
    *,
    user_id: int,
    question: str,
    top_k: Optional[int] = None,
) -> list[RetrievedChunk]:
    query_embedding = generate_embedding(question, is_query=True)
    if not query_embedding or not has_chunk_embedding_storage(db):
        return []

    limit = min(max(top_k or settings.rag_top_k, 1), 8)
    rows = db.execute(
        text(
            """
            SELECT c.item_id,
                   COALESCE(i.title, i.url) AS title,
                   i.url,
                   c.chunk_index,
                   c.content,
                   1 - (c.embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM item_chunks c
            JOIN items i ON i.id = c.item_id
            WHERE c.user_id = :user_id
              AND i.user_id = :user_id
              AND c.embedding IS NOT NULL
              AND c.embedding_provider = :provider
              AND c.embedding_model = :model
              AND c.embedding_dimensions = :dimensions
              AND 1 - (c.embedding <=> CAST(:query_embedding AS vector)) >= :min_similarity
            ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
            """
        ),
        {
            "user_id": user_id,
            "query_embedding": format_vector(query_embedding.values),
            "provider": query_embedding.provider,
            "model": query_embedding.model,
            "dimensions": query_embedding.dimensions,
            "min_similarity": settings.rag_min_similarity,
            "limit": limit,
        },
    ).all()

    return [
        RetrievedChunk(
            item_id=row.item_id,
            title=row.title,
            url=row.url,
            chunk_index=row.chunk_index,
            content=row.content,
            similarity=float(row.similarity),
        )
        for row in rows
    ]


def load_item_for_indexing(db: Session, item_id: int, user_id: int) -> Optional[Item]:
    return db.scalar(
        select(Item)
        .where(Item.id == item_id, Item.user_id == user_id)
        .options(selectinload(Item.tags))
    )
