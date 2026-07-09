"""Normalize and deduplicate localities.

Revision ID: 20260709_0005
Revises: 20260708_0004
Create Date: 2026-07-09
"""

from __future__ import annotations

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "20260709_0005"
down_revision = "20260708_0004"
branch_labels = None
depends_on = None


COUNTRY_LABELS = {
    "espana": "España",
    "spain": "España",
    "marruecos": "Marruecos",
    "morocco": "Marruecos",
    "mexico": "México",
    "japon": "Japón",
    "turquia": "Turquía",
    "sudafrica": "Sudáfrica",
    "reino unido": "Reino Unido",
    "united kingdom": "Reino Unido",
    "estados unidos": "Estados Unidos",
    "united states": "Estados Unidos",
    "usa": "Estados Unidos",
}


def clean_text(value: object) -> str | None:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def normalized_text_key(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_country(value: object) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return COUNTRY_LABELS.get(normalized_text_key(text), text)


def row_value(row, field: str):
    return row[field]


def valid_coordinate(latitude: object, longitude: object) -> bool:
    if latitude is None or longitude is None:
        return False
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def locality_key(row) -> str | None:
    country = canonical_country(row_value(row, "country"))
    text_parts = {
        "country": normalized_text_key(country),
        "region": normalized_text_key(row_value(row, "region")),
        "mine": normalized_text_key(row_value(row, "mine")),
        "name": normalized_text_key(row_value(row, "name")),
    }
    if any(text_parts.values()):
        return "|".join(f"{field}:{value}" for field, value in text_parts.items())
    if valid_coordinate(row_value(row, "latitude"), row_value(row, "longitude")):
        return f"coords:{float(row_value(row, 'latitude')):.5f},{float(row_value(row, 'longitude')):.5f}"
    return None


def choose_value(rows, field: str):
    for row in rows:
        value = clean_text(row_value(row, field))
        if value:
            return value
    return None


def choose_coordinate(rows, field: str):
    for row in rows:
        value = row_value(row, field)
        if value is not None:
            return value
    return None


def locality_score(row) -> tuple[int, int, int]:
    has_coordinates = int(valid_coordinate(row_value(row, "latitude"), row_value(row, "longitude")))
    filled_fields = sum(
        1 for field in ("country", "region", "mine", "name") if clean_text(row_value(row, field))
    )
    return has_coordinates, filled_fields, -int(row_value(row, "id"))


def upgrade() -> None:
    op.add_column("localities", sa.Column("normalized_key", sa.String(length=900), nullable=True))
    connection = op.get_bind()

    rows = (
        connection.execute(
            sa.text(
                """
                SELECT id, mindat_locality_id, name, mine, region, country, latitude, longitude, notes
                FROM localities
                ORDER BY id
                """
            )
        )
        .mappings()
        .all()
    )

    groups: dict[str, list] = {}
    for row in rows:
        key = locality_key(row)
        if key:
            groups.setdefault(key, []).append(row)
        else:
            connection.execute(
                sa.text("UPDATE localities SET normalized_key = NULL WHERE id = :id"),
                {"id": row_value(row, "id")},
            )

    for key, group in groups.items():
        canonical = max(group, key=locality_score)
        ordered_for_values = [canonical, *[row for row in group if row_value(row, "id") != row_value(canonical, "id")]]
        values = {
            "id": row_value(canonical, "id"),
            "normalized_key": key,
            "mindat_locality_id": row_value(canonical, "mindat_locality_id")
            or next((row_value(row, "mindat_locality_id") for row in group if row_value(row, "mindat_locality_id")), None),
            "name": choose_value(ordered_for_values, "name"),
            "mine": choose_value(ordered_for_values, "mine"),
            "region": choose_value(ordered_for_values, "region"),
            "country": canonical_country(choose_value(ordered_for_values, "country")),
            "latitude": choose_coordinate(ordered_for_values, "latitude"),
            "longitude": choose_coordinate(ordered_for_values, "longitude"),
            "notes": choose_value(ordered_for_values, "notes"),
        }
        connection.execute(
            sa.text(
                """
                UPDATE localities
                SET normalized_key = :normalized_key,
                    mindat_locality_id = :mindat_locality_id,
                    name = :name,
                    mine = :mine,
                    region = :region,
                    country = :country,
                    latitude = :latitude,
                    longitude = :longitude,
                    notes = :notes
                WHERE id = :id
                """
            ),
            values,
        )

        duplicate_ids = [row_value(row, "id") for row in group if row_value(row, "id") != row_value(canonical, "id")]
        for duplicate_id in duplicate_ids:
            connection.execute(
                sa.text(
                    """
                    UPDATE collection_items
                    SET locality_id = :canonical_id
                    WHERE locality_id = :duplicate_id
                    """
                ),
                {"canonical_id": row_value(canonical, "id"), "duplicate_id": duplicate_id},
            )
            connection.execute(
                sa.text("DELETE FROM localities WHERE id = :duplicate_id"),
                {"duplicate_id": duplicate_id},
            )

    op.create_index("ix_localities_normalized_key", "localities", ["normalized_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_localities_normalized_key", table_name="localities")
    op.drop_column("localities", "normalized_key")
