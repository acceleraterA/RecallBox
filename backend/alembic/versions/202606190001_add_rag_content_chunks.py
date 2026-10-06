"""add rag content chunks

Revision ID: 202606190001
Revises: 202606180001
Create Date: 2026-06-19 00:01:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "202606190001"
down_revision: Union[str, None] = "202606180001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("content_text", sa.Text(), nullable=True))
    op.add_column(
        "items",
        sa.Column(
            "content_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_items_content_status"), "items", ["content_status"], unique=False)

    op.create_table(
        "item_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_provider", sa.String(length=64), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "chunk_index", name="uq_item_chunks_item_index"),
    )
    op.create_index(op.f("ix_item_chunks_id"), "item_chunks", ["id"], unique=False)
    op.create_index(op.f("ix_item_chunks_item_id"), "item_chunks", ["item_id"], unique=False)
    op.create_index(op.f("ix_item_chunks_user_id"), "item_chunks", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_item_chunks_embedding_provider"),
        "item_chunks",
        ["embedding_provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_item_chunks_embedding_model"),
        "item_chunks",
        ["embedding_model"],
        unique=False,
    )

    if context.is_offline_mode():
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE item_chunks ADD COLUMN embedding vector")
        return

    connection = op.get_bind()
    has_pgvector = connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')")
    )
    if has_pgvector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE item_chunks ADD COLUMN embedding vector")


def downgrade() -> None:
    op.drop_table("item_chunks")
    op.drop_index(op.f("ix_items_content_status"), table_name="items")
    op.drop_column("items", "content_status")
    op.drop_column("items", "content_text")
