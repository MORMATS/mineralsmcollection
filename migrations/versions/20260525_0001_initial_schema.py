"""Initial schema.

Revision ID: 20260525_0001
Revises:
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260525_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chakras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=80), nullable=True),
        sa.Column("element", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "localities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mindat_locality_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("mine", sa.String(length=255), nullable=True),
        sa.Column("region", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mindat_locality_id"),
    )
    op.create_index("ix_localities_country", "localities", ["country"])

    op.create_table(
        "mineral_species",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mindat_id", sa.Integer(), nullable=True),
        sa.Column("rruff_id", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("formula", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=160), nullable=True),
        sa.Column("crystal_system", sa.String(length=120), nullable=True),
        sa.Column("hardness_min", sa.Float(), nullable=True),
        sa.Column("hardness_max", sa.Float(), nullable=True),
        sa.Column("color", sa.String(length=255), nullable=True),
        sa.Column("luster", sa.String(length=160), nullable=True),
        sa.Column("streak", sa.String(length=160), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("api_raw_json", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mindat_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_mineral_species_name", "mineral_species", ["name"])

    op.create_table(
        "zodiac_signs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "collection_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=180), nullable=True),
        sa.Column("mineral_id", sa.Integer(), nullable=False),
        sa.Column("locality_id", sa.Integer(), nullable=True),
        sa.Column("acquisition_date", sa.Date(), nullable=True),
        sa.Column("acquisition_source", sa.String(length=255), nullable=True),
        sa.Column("purchase_price", sa.Float(), nullable=True),
        sa.Column("sale_price", sa.Float(), nullable=True),
        sa.Column("sold", sa.Boolean(), nullable=False),
        sa.Column("sold_at", sa.Date(), nullable=True),
        sa.Column("purchase_link", sa.String(length=800), nullable=True),
        sa.Column("special_features", sa.Text(), nullable=True),
        sa.Column("secondary_minerals", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["locality_id"], ["localities.id"]),
        sa.ForeignKeyConstraint(["mineral_id"], ["mineral_species.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_code", name="uq_collection_item_code"),
    )
    op.create_index("ix_collection_items_item_code", "collection_items", ["item_code"])
    op.create_index("ix_collection_items_sold", "collection_items", ["sold"])

    op.create_table(
        "mineral_chakras",
        sa.Column("mineral_id", sa.Integer(), nullable=False),
        sa.Column("chakra_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["chakra_id"], ["chakras.id"]),
        sa.ForeignKeyConstraint(["mineral_id"], ["mineral_species.id"]),
        sa.PrimaryKeyConstraint("mineral_id", "chakra_id"),
    )

    op.create_table(
        "mineral_zodiac_signs",
        sa.Column("mineral_id", sa.Integer(), nullable=False),
        sa.Column("zodiac_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["mineral_id"], ["mineral_species.id"]),
        sa.ForeignKeyConstraint(["zodiac_id"], ["zodiac_signs.id"]),
        sa.PrimaryKeyConstraint("mineral_id", "zodiac_id"),
    )

    op.create_table(
        "item_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("caption", sa.String(length=255), nullable=True),
        sa.Column("is_cover", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["collection_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("item_images")
    op.drop_table("mineral_zodiac_signs")
    op.drop_table("mineral_chakras")
    op.drop_index("ix_collection_items_sold", table_name="collection_items")
    op.drop_index("ix_collection_items_item_code", table_name="collection_items")
    op.drop_table("collection_items")
    op.drop_table("zodiac_signs")
    op.drop_index("ix_mineral_species_name", table_name="mineral_species")
    op.drop_table("mineral_species")
    op.drop_index("ix_localities_country", table_name="localities")
    op.drop_table("localities")
    op.drop_table("chakras")
