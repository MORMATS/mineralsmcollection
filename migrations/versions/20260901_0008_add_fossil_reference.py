"""Add the generic fossil reference used by the item editor.

Revision ID: 20260901_0008
Revises: 20260817_0007
Create Date: 2026-09-01
"""

from alembic import op


revision = "20260901_0008"
down_revision = "20260817_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO mineral_species (name, category, description, updated_at)
        SELECT
            'Fósil',
            'Fósil',
            'Referencia genérica para piezas fósiles sin una especie paleontológica específica.',
            CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM mineral_species WHERE name = 'Fósil'
        )
        """
    )


def downgrade() -> None:
    # Keep the reference because collection items may already depend on it.
    pass
