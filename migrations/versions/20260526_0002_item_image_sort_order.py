"""Add explicit image ordering.

Revision ID: 20260526_0002
Revises: 20260525_0001
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_0002"
down_revision = "20260525_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("item_images", sa.Column("sort_order", sa.Integer(), nullable=True))
    op.execute("UPDATE item_images SET sort_order = id WHERE sort_order IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("item_images") as batch_op:
        batch_op.drop_column("sort_order")
