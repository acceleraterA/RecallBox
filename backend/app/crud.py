from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.embeddings import EmbeddingResult, format_vector
from app.models import Item, Tag, User


def normalize_tag(name: str) -> Optional[str]:
    normalized = " ".join(name.strip().lower().split())
    if not normalized:
        return None
    return normalized[:80]


def get_or_create_default_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == settings.default_user_email))
    if user:
        return user

    user = User(email=settings.default_user_email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_auth_user(
    db: Session,
    *,
    provider: str,
    subject: str,
    email: Optional[str],
) -> User:
    user = db.scalar(
        select(User).where(User.auth_provider == provider, User.auth_subject == subject)
    )
    normalized_email = email or f"{provider}:{subject}@recallbox.local"

    if user:
        if user.email != normalized_email:
            user.email = normalized_email
            db.commit()
            db.refresh(user)
        return user

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user:
        user.auth_provider = provider
        user.auth_subject = subject
        db.commit()
        db.refresh(user)
        return user

    user = User(email=normalized_email, auth_provider=provider, auth_subject=subject)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_item(db: Session, item_id: int, user_id: int) -> Optional[Item]:
    return db.scalar(
        select(Item)
        .where(Item.id == item_id, Item.user_id == user_id)
        .options(selectinload(Item.tags))
    )


def get_item_by_url(db: Session, *, user_id: int, url: str) -> Optional[Item]:
    return db.scalar(
        select(Item)
        .where(Item.user_id == user_id, Item.url == url)
        .options(selectinload(Item.tags))
    )


def create_item(db: Session, *, user_id: int, url: str, note: Optional[str], platform: str) -> Item:
    item = Item(user_id=user_id, url=url, note=note, platform=platform, status="processing")
    db.add(item)
    db.flush()
    return item


def list_items(
    db: Session,
    *,
    user_id: int,
    q: Optional[str] = None,
    platform: Optional[str] = None,
    tag: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Item]:
    statement = (
        select(Item)
        .where(Item.user_id == user_id)
        .options(selectinload(Item.tags))
        .order_by(Item.created_at.desc(), Item.id.desc())
        .offset(offset)
        .limit(limit)
    )

    if platform:
        statement = statement.where(Item.platform == platform)

    normalized_tag = normalize_tag(tag) if tag else None
    if normalized_tag:
        statement = statement.where(Item.tags.any(Tag.name == normalized_tag))

    if date_from:
        statement = statement.where(Item.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        statement = statement.where(Item.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Item.url.ilike(pattern),
                Item.title.ilike(pattern),
                Item.description.ilike(pattern),
                Item.summary.ilike(pattern),
                Item.note.ilike(pattern),
                Item.tags.any(Tag.name.ilike(pattern)),
            )
        )

    return list(db.scalars(statement).all())


def get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    normalized_names = []
    seen = set()
    for name in names:
        normalized = normalize_tag(name)
        if normalized and normalized not in seen:
            normalized_names.append(normalized)
            seen.add(normalized)

    if not normalized_names:
        return []

    existing = {
        tag.name: tag
        for tag in db.scalars(select(Tag).where(Tag.name.in_(normalized_names))).all()
    }

    tags: list[Tag] = []
    for name in normalized_names:
        tag = existing.get(name)
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
        tags.append(tag)

    db.flush()
    return tags


def set_item_tags(db: Session, item: Item, names: list[str]) -> None:
    item.tags = get_or_create_tags(db, names)


def list_tags(db: Session, *, user_id: int) -> list[str]:
    statement = (
        select(Tag.name)
        .where(Tag.items.any(Item.user_id == user_id))
        .distinct()
        .order_by(Tag.name)
    )
    return list(db.scalars(statement).all())


def delete_item(db: Session, item: Item) -> None:
    db.delete(item)


def has_embedding_storage(db: Session) -> bool:
    return bool(
        db.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'items' AND column_name = 'embedding'
                )
                """
            )
        )
    )


def set_item_embedding_text(db: Session, *, item: Item, embedding_text: str) -> None:
    item.embedding_text = embedding_text
    item.embedding_provider = None
    item.embedding_model = None
    item.embedding_dimensions = None

    if has_embedding_storage(db):
        db.execute(
            text(
                """
                UPDATE items
                SET embedding_text = :embedding_text,
                    embedding = NULL,
                    embedding_provider = NULL,
                    embedding_model = NULL,
                    embedding_dimensions = NULL
                WHERE id = :item_id
                """
            ),
            {"item_id": item.id, "embedding_text": embedding_text},
        )


def set_item_embedding(
    db: Session,
    *,
    item: Item,
    embedding_text: str,
    embedding: EmbeddingResult,
) -> None:
    if not has_embedding_storage(db):
        item.embedding_text = embedding_text
        return

    db.execute(
        text(
            """
            UPDATE items
            SET embedding_text = :embedding_text,
                embedding = CAST(:embedding AS vector),
                embedding_provider = :embedding_provider,
                embedding_model = :embedding_model,
                embedding_dimensions = :embedding_dimensions
            WHERE id = :item_id
            """
        ),
        {
            "item_id": item.id,
            "embedding_text": embedding_text,
            "embedding": format_vector(embedding.values),
            "embedding_provider": embedding.provider,
            "embedding_model": embedding.model,
            "embedding_dimensions": embedding.dimensions,
        },
    )
    item.embedding_text = embedding_text
    item.embedding_provider = embedding.provider
    item.embedding_model = embedding.model
    item.embedding_dimensions = embedding.dimensions


def list_items_semantic(
    db: Session,
    *,
    user_id: int,
    query_embedding: EmbeddingResult,
    platform: Optional[str] = None,
    tag: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Item]:
    where_clauses = [
        "i.user_id = :user_id",
        "i.embedding IS NOT NULL",
        "i.embedding_provider = :embedding_provider",
        "i.embedding_model = :embedding_model",
        "i.embedding_dimensions = :embedding_dimensions",
        "1 - (i.embedding <=> CAST(:query_embedding AS vector)) >= :min_similarity",
    ]
    params: dict[str, object] = {
        "user_id": user_id,
        "query_embedding": format_vector(query_embedding.values),
        "embedding_provider": query_embedding.provider,
        "embedding_model": query_embedding.model,
        "embedding_dimensions": query_embedding.dimensions,
        "min_similarity": settings.embedding_min_similarity,
        "limit": limit,
        "offset": offset,
    }

    if platform:
        where_clauses.append("i.platform = :platform")
        params["platform"] = platform

    normalized_tag = normalize_tag(tag) if tag else None
    if normalized_tag:
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM item_tags it
                JOIN tags t ON t.id = it.tag_id
                WHERE it.item_id = i.id AND t.name = :tag
            )
            """
        )
        params["tag"] = normalized_tag

    if date_from:
        where_clauses.append("i.created_at >= :date_from")
        params["date_from"] = datetime.combine(date_from, time.min)
    if date_to:
        where_clauses.append("i.created_at < :date_to")
        params["date_to"] = datetime.combine(date_to + timedelta(days=1), time.min)

    statement = text(
        f"""
        SELECT i.id
        FROM items i
        WHERE {' AND '.join(where_clauses)}
        ORDER BY i.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :limit OFFSET :offset
        """
    )
    ids = [row.id for row in db.execute(statement, params).all()]
    if not ids:
        return []

    items = db.scalars(
        select(Item)
        .where(Item.id.in_(ids), Item.user_id == user_id)
        .options(selectinload(Item.tags))
    ).all()
    by_id = {item.id: item for item in items}
    return [by_id[item_id] for item_id in ids if item_id in by_id]
