from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import crud
from app.embeddings import generate_embedding
from app.models import Item
from app.rag import retrieve_chunks


@dataclass(frozen=True)
class ToolContext:
    db: Session
    user_id: int


def _title(item: Item) -> str:
    return item.title or item.description or item.url


def _bookmark_summary(item: Item, rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "bookmark_id": item.id,
        "title": _title(item),
        "url": item.url,
        "platform": item.platform,
        "note": item.note,
        "tags": [tag.name for tag in sorted(item.tags, key=lambda tag: tag.name)],
        "created_at": item.created_at.isoformat(),
    }


def search_bookmarks_tool(
    context: ToolContext,
    *,
    query: str,
    semantic: bool = True,
    platform: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 5,
) -> dict[str, Any]:
    limit = min(max(limit, 1), 10)
    query_embedding = generate_embedding(query, is_query=True) if semantic and query else None
    if query_embedding and crud.has_embedding_storage(context.db):
        items = crud.list_items_semantic(
            context.db,
            user_id=context.user_id,
            query_embedding=query_embedding,
            platform=platform,
            tag=tag,
            limit=limit,
            offset=0,
        )
        mode = "semantic"
    else:
        items = crud.list_items(
            context.db,
            user_id=context.user_id,
            q=query,
            platform=platform,
            tag=tag,
            limit=limit,
            offset=0,
        )
        mode = "keyword"

    return {
        "mode": mode,
        "bookmarks": [_bookmark_summary(item, rank=index) for index, item in enumerate(items, start=1)],
    }


def _load_bookmarks(context: ToolContext, bookmark_ids: list[int]) -> list[Item]:
    if not bookmark_ids:
        return []
    return list(
        context.db.scalars(
            select(Item)
            .where(Item.user_id == context.user_id, Item.id.in_(bookmark_ids))
            .options(selectinload(Item.tags), selectinload(Item.chunks))
        ).all()
    )


def get_bookmark_content_tool(
    context: ToolContext,
    *,
    bookmark_ids: Optional[list[int]] = None,
    query: Optional[str] = None,
    top_k: int = 5,
) -> dict[str, Any]:
    top_k = min(max(top_k, 1), 8)
    passages: list[dict[str, Any]] = []

    if bookmark_ids:
        for item in _load_bookmarks(context, bookmark_ids):
            chunks = item.chunks[:top_k] if item.chunks else []
            if chunks:
                for chunk in chunks:
                    passages.append(
                        {
                            "bookmark_id": item.id,
                            "title": _title(item),
                            "url": item.url,
                            "chunk_index": chunk.chunk_index,
                            "excerpt": " ".join(chunk.content.split())[:600],
                        }
                    )
            else:
                fallback = item.content_text or item.description or item.summary or item.note or ""
                passages.append(
                    {
                        "bookmark_id": item.id,
                        "title": _title(item),
                        "url": item.url,
                        "chunk_index": None,
                        "excerpt": " ".join(fallback.split())[:600],
                    }
                )
    elif query:
        chunks = retrieve_chunks(
            context.db,
            user_id=context.user_id,
            question=query,
            top_k=top_k,
        )
        passages = [
            {
                "bookmark_id": chunk.item_id,
                "title": chunk.title,
                "url": chunk.url,
                "chunk_index": chunk.chunk_index,
                "excerpt": " ".join(chunk.content.split())[:600],
                "similarity": round(chunk.similarity, 4),
            }
            for chunk in chunks
        ]

    return {"passages": passages}


def list_collections_tool(context: ToolContext) -> dict[str, Any]:
    platforms = list(
        context.db.scalars(
            select(Item.platform)
            .where(Item.user_id == context.user_id)
            .distinct()
            .order_by(Item.platform)
        ).all()
    )
    return {
        "tags": crud.list_tags(context.db, user_id=context.user_id),
        "platforms": platforms,
    }


def create_note_tool(
    context: ToolContext,
    *,
    bookmark_id: int,
    note: str,
    confirmed: bool = False,
) -> dict[str, Any]:
    item = crud.get_item(context.db, item_id=bookmark_id, user_id=context.user_id)
    if not item:
        return {"status": "not_found", "bookmark_id": bookmark_id}

    note = note.strip()[:5000]
    if not confirmed:
        return {
            "status": "needs_confirmation",
            "bookmark_id": bookmark_id,
            "title": _title(item),
            "note": note,
        }

    item.note = note
    context.db.commit()
    context.db.refresh(item)
    return {
        "status": "updated",
        "bookmark_id": item.id,
        "title": _title(item),
        "note": item.note,
    }

