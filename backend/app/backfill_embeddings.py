from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import crud
from app.database import SessionLocal
from app.embeddings import build_item_embedding_text, generate_embedding
from app.models import Item


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    updated = 0
    failed = 0

    with SessionLocal() as db:
        if not crud.has_embedding_storage(db):
            raise SystemExit("Embedding storage is unavailable. Run alembic upgrade head first.")

        items = db.scalars(select(Item).options(selectinload(Item.tags))).all()
        for item in items:
            embedding_text = build_item_embedding_text(
                item,
                [tag.name for tag in item.tags],
            )
            crud.set_item_embedding_text(db, item=item, embedding_text=embedding_text)
            embedding = generate_embedding(embedding_text)
            if not embedding:
                failed += 1
                db.commit()
                continue

            crud.set_item_embedding(
                db,
                item=item,
                embedding_text=embedding_text,
                embedding=embedding,
            )
            db.commit()
            updated += 1
            print(
                f"Embedded item {item.id} with "
                f"{embedding.provider}/{embedding.model} ({embedding.dimensions} dimensions)"
            )

    print(f"Backfill complete: {updated} embedded, {failed} failed")


if __name__ == "__main__":
    main()
