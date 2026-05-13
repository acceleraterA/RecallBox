from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.llm import generate_enrichment
from app.metadata import extract_metadata
from app.platform import detect_platform
from app.schemas import ItemCreate, ItemOut, ItemUpdate
from app.share import extract_first_url, inferred_tags, title_from_share_text

router = APIRouter(prefix="/items", tags=["items"])


def _serialize_item(item) -> ItemOut:
    return ItemOut(
        id=item.id,
        url=item.url,
        platform=item.platform,
        title=item.title,
        description=item.description,
        summary=item.summary,
        note=item.note,
        thumbnail_url=item.thumbnail_url,
        status=item.status,
        tags=[tag.name for tag in sorted(item.tags, key=lambda tag: tag.name)],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> ItemOut:
    user = crud.get_or_create_default_user(db)
    raw_input = payload.url.strip()
    url = extract_first_url(raw_input)
    if not url:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Paste a valid URL")

    item = crud.create_item(
        db,
        user_id=user.id,
        url=url,
        note=payload.note,
        platform=detect_platform(url),
    )

    metadata = extract_metadata(url)
    item.title = metadata.title
    item.description = metadata.description
    item.thumbnail_url = metadata.thumbnail_url
    item.status = "failed" if metadata.error else "ready"
    if not item.title:
        item.title = title_from_share_text(raw_input, url)

    enrichment = generate_enrichment(
        title=item.title,
        description=item.description,
        note=item.note,
    )
    item.summary = enrichment.summary
    tags = inferred_tags(url, raw_input)
    if enrichment.tags:
        tags.extend(enrichment.tags)
    if tags:
        crud.set_item_tags(db, item, tags)

    db.commit()
    db.refresh(item)
    return _serialize_item(item)


@router.get("", response_model=list[ItemOut])
def list_items(
    q: Optional[str] = None,
    platform: Optional[str] = None,
    tag: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ItemOut]:
    user = crud.get_or_create_default_user(db)
    items = crud.list_items(
        db,
        user_id=user.id,
        q=q,
        platform=platform,
        tag=tag,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [_serialize_item(item) for item in items]


@router.get("/tags", response_model=list[str])
def list_tags(db: Session = Depends(get_db)) -> list[str]:
    user = crud.get_or_create_default_user(db)
    return crud.list_tags(db, user_id=user.id)


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)) -> ItemOut:
    user = crud.get_or_create_default_user(db)
    item = crud.get_item(db, item_id=item_id, user_id=user.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return _serialize_item(item)


@router.patch("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)) -> ItemOut:
    user = crud.get_or_create_default_user(db)
    item = crud.get_item(db, item_id=item_id, user_id=user.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if "note" in payload.model_fields_set:
        item.note = payload.note
    if "thumbnail_url" in payload.model_fields_set:
        item.thumbnail_url = payload.thumbnail_url
    if payload.tags is not None:
        crud.set_item_tags(db, item, payload.tags)

    db.commit()
    db.refresh(item)
    return _serialize_item(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> Response:
    user = crud.get_or_create_default_user(db)
    item = crud.get_item(db, item_id=item_id, user_id=user.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    crud.delete_item(db, item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
