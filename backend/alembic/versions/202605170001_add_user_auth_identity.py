"""add user auth identity

Revision ID: 202605170001
Revises: 202605130001
Create Date: 2026-05-17 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605170001"
down_revision: Union[str, None] = "202605130001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_provider", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("auth_subject", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_auth_provider"), "users", ["auth_provider"], unique=False)
    op.create_index(op.f("ix_users_auth_subject"), "users", ["auth_subject"], unique=False)
    op.create_unique_constraint("uq_users_auth_identity", "users", ["auth_provider", "auth_subject"])


def downgrade() -> None:
    op.drop_constraint("uq_users_auth_identity", "users", type_="unique")
    op.drop_index(op.f("ix_users_auth_subject"), table_name="users")
    op.drop_index(op.f("ix_users_auth_provider"), table_name="users")
    op.drop_column("users", "auth_subject")
    op.drop_column("users", "auth_provider")
