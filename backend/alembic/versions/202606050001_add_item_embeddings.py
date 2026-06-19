"""add item embeddings

Revision ID: 202606050001
Revises: 202605170001
Create Date: 2026-06-05 00:01:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "202606050001"
down_revision: Union[str, None] = "202605170001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("embedding_text", sa.Text(), nullable=True))

    if context.is_offline_mode():
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE items ADD COLUMN embedding vector(1536)")
        return

    connection = op.get_bind()
    has_pgvector = connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')")
    )
    if has_pgvector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE items ADD COLUMN embedding vector(1536)")


def downgrade() -> None:
    op.execute("ALTER TABLE items DROP COLUMN IF EXISTS embedding")
    op.drop_column("items", "embedding_text")
