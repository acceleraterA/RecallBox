"""add embedding provider metadata

Revision ID: 202606180001
Revises: 202606050001
Create Date: 2026-06-18 00:01:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "202606180001"
down_revision: Union[str, None] = "202606050001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("embedding_provider", sa.String(length=64), nullable=True))
    op.add_column("items", sa.Column("embedding_model", sa.String(length=255), nullable=True))
    op.add_column("items", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_items_embedding_provider"), "items", ["embedding_provider"], unique=False)
    op.create_index(op.f("ix_items_embedding_model"), "items", ["embedding_model"], unique=False)

    if context.is_offline_mode():
        op.execute("ALTER TABLE items ALTER COLUMN embedding TYPE vector USING embedding::vector")
        return

    connection = op.get_bind()
    has_embedding = connection.scalar(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'items' AND column_name = 'embedding'
            )
            """
        )
    )
    if has_embedding:
        op.execute("ALTER TABLE items ALTER COLUMN embedding TYPE vector USING embedding::vector")


def downgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "UPDATE items SET embedding = NULL "
            "WHERE embedding_dimensions IS DISTINCT FROM 1536"
        )
        op.execute(
            "ALTER TABLE items ALTER COLUMN embedding TYPE vector(1536) "
            "USING embedding::vector(1536)"
        )
    else:
        connection = op.get_bind()
        has_embedding = connection.scalar(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'items' AND column_name = 'embedding'
                )
                """
            )
        )
        if has_embedding:
            op.execute(
                "UPDATE items SET embedding = NULL "
                "WHERE embedding_dimensions IS DISTINCT FROM 1536"
            )
            op.execute(
                "ALTER TABLE items ALTER COLUMN embedding TYPE vector(1536) "
                "USING embedding::vector(1536)"
            )

    op.drop_index(op.f("ix_items_embedding_model"), table_name="items")
    op.drop_index(op.f("ix_items_embedding_provider"), table_name="items")
    op.drop_column("items", "embedding_dimensions")
    op.drop_column("items", "embedding_model")
    op.drop_column("items", "embedding_provider")
