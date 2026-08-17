"""Store complete Mindat locality details.

Revision ID: 20260817_0007
Revises: 20260709_0006
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260817_0007"
down_revision = "20260709_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("localities", sa.Column("source_url", sa.String(length=500), nullable=True))
    op.add_column("localities", sa.Column("api_raw_json", sa.Text(), nullable=True))
    op.add_column("localities", sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("localities", "updated_at")
    op.drop_column("localities", "api_raw_json")
    op.drop_column("localities", "source_url")
