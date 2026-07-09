"""Add collection item type.

Revision ID: 20260708_0003
Revises: 20260526_0002
Create Date: 2026-07-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260708_0003"
down_revision = "20260526_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "collection_items",
        sa.Column(
            "item_type",
            sa.String(length=20),
            server_default="mineral",
            nullable=False,
        ),
    )
    op.create_index("ix_collection_items_item_type", "collection_items", ["item_type"])


def downgrade() -> None:
    op.drop_index("ix_collection_items_item_type", table_name="collection_items")
    with op.batch_alter_table("collection_items") as batch_op:
        batch_op.drop_column("item_type")
