from __future__ import annotations

import argparse
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.metadata import extract_metadata
from app.models import Item
from app.rag import has_chunk_embedding_storage, index_item_content


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and embed saved-link content")
    parser.add_argument("--item-id", type=int, help="Index one item")
    parser.add_argument("--limit", type=int, help="Maximum number of items to process")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    indexed = 0
    failed = 0

    with SessionLocal() as db:
        if not has_chunk_embedding_storage(db):
            raise SystemExit("Chunk embedding storage is unavailable. Run alembic upgrade head first.")

        statement = select(Item).options(selectinload(Item.tags)).order_by(Item.id)
        if args.item_id:
            statement = statement.where(Item.id == args.item_id)
        if args.limit:
            statement = statement.limit(max(args.limit, 1))
        items = db.scalars(statement).all()
        for item in items:
            metadata = extract_metadata(item.url)
            if metadata.content_text:
                item.content_text = metadata.content_text
            if not item.title and metadata.title:
                item.title = metadata.title
            if not item.description and metadata.description:
                item.description = metadata.description

            count = index_item_content(db, item)
            db.commit()
            if count:
                indexed += 1
                print(f"Indexed item {item.id}: {count} embedded chunks")
            else:
                failed += 1
                print(f"Could not index item {item.id}")

    print(f"RAG backfill complete: {indexed} indexed, {failed} failed")


if __name__ == "__main__":
    main()
