"""Add mineral elements field.

Revision ID: 20260709_0006
Revises: 20260709_0005
Create Date: 2026-07-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0006"
down_revision = "20260709_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mineral_species", sa.Column("elements", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("mineral_species", "elements")
