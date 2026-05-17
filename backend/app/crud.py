from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
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
