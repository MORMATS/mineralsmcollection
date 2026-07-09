"""Infer pendant type for existing visible names.

Revision ID: 20260708_0004
Revises: 20260708_0003
Create Date: 2026-07-08
"""

from __future__ import annotations

from alembic import op


revision = "20260708_0004"
down_revision = "20260708_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE collection_items
        SET item_type = 'pendant'
        WHERE item_type = 'mineral'
          AND lower(coalesce(display_name, '')) LIKE '%colgante%'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE collection_items
        SET item_type = 'mineral'
        WHERE item_type = 'pendant'
          AND lower(coalesce(display_name, '')) LIKE '%colgante%'
        """
    )
