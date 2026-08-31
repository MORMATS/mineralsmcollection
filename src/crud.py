from __future__ import annotations

import re

from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload, selectinload, Session

from src.image_utils import delete_uploaded_images
from src.item_types import ITEM_TYPE_FILTER_OPTIONS, item_type_from_filter, normalize_item_type
from src.models import CollectionItem, MineralSpecies, Locality, Chakra


ITEM_CODE_RE = re.compile(r"^([A-Za-z]+)-(\d+)$")


def normalize_item_code(value: str, prefix: str = "MIN", width: int = 4) -> str:
    value = value.strip()
    if not value:
        return ""

    normalized_prefix = prefix.strip().upper() or "MIN"
    if value.isdigit():
        return f"{normalized_prefix}-{int(value):0{width}d}"

    match = ITEM_CODE_RE.match(value)
    if match:
        return f"{match.group(1).upper()}-{int(match.group(2)):0{width}d}"

    return value.upper()


def generate_next_item_code(db: Session, prefix: str = "MIN", width: int = 4) -> str:
    """Return the next collection code using the current MIN-0001 style."""
    normalized_prefix = prefix.strip().upper() or "MIN"
    codes = (
        db.execute(
            select(CollectionItem.item_code).where(
                CollectionItem.item_code.ilike(f"{normalized_prefix}-%")
            )
        )
        .scalars()
        .all()
    )

    max_number = 0
    for code in codes:
        match = ITEM_CODE_RE.match(code.strip())
        if not match or match.group(1).upper() != normalized_prefix:
            continue
        max_number = max(max_number, int(match.group(2)))

    return f"{normalized_prefix}-{max_number + 1:0{width}d}"


def list_collection_items(
    db: Session,
    text: str | None = None,
    sold: bool | None = None,
    item_type: str | None = None,
    mineral_name: str | None = None,
    country: str | None = None,
    chakra: str | None = None,
    locality_ids: list[int] | None = None,
):
    stmt = (
        select(CollectionItem)
        .options(
            selectinload(CollectionItem.mineral).selectinload(MineralSpecies.chakras),
            selectinload(CollectionItem.mineral).selectinload(MineralSpecies.zodiac_signs),
            joinedload(CollectionItem.locality),
            selectinload(CollectionItem.images),
        )
        .join(CollectionItem.mineral)
        .outerjoin(CollectionItem.locality)
    )

    if text:
        clean_text = text.strip()
        like = f"%{clean_text}%"
        normalized_code = normalize_item_code(clean_text)
        stmt = stmt.where(
            or_(
                CollectionItem.item_code.ilike(like),
                CollectionItem.item_code == normalized_code,
                CollectionItem.display_name.ilike(like),
                MineralSpecies.name.ilike(like),
                CollectionItem.secondary_minerals.ilike(like),
                CollectionItem.special_features.ilike(like),
            )
        )

    if sold is not None:
        stmt = stmt.where(CollectionItem.sold == sold)

    if item_type:
        stmt = stmt.where(CollectionItem.item_type == normalize_item_type(item_type))

    if mineral_name and mineral_name != "Todos":
        stmt = stmt.where(MineralSpecies.name == mineral_name)

    if country and country != "Todos":
        stmt = stmt.where(Locality.country == country)

    if locality_ids:
        stmt = stmt.where(CollectionItem.locality_id.in_(locality_ids))

    if chakra and chakra != "Todos":
        stmt = stmt.join(MineralSpecies.chakras).where(Chakra.name == chakra)

    stmt = stmt.order_by(CollectionItem.created_at.desc())
    return db.execute(stmt).unique().scalars().all()


def list_collection_map_items(
    db: Session,
    sold: bool | None = None,
    item_type: str | None = None,
    mineral_name: str | None = None,
    country: str | None = None,
):
    stmt = (
        select(CollectionItem)
        .options(
            joinedload(CollectionItem.mineral),
            joinedload(CollectionItem.locality),
            selectinload(CollectionItem.images),
        )
        .join(CollectionItem.mineral)
        .outerjoin(CollectionItem.locality)
    )

    if sold is not None:
        stmt = stmt.where(CollectionItem.sold == sold)

    if item_type:
        stmt = stmt.where(CollectionItem.item_type == normalize_item_type(item_type))

    if mineral_name and mineral_name != "Todos":
        stmt = stmt.where(MineralSpecies.name == mineral_name)

    if country and country != "Todos":
        stmt = stmt.where(Locality.country == country)

    stmt = stmt.order_by(CollectionItem.created_at.desc())
    return db.execute(stmt).unique().scalars().all()


def get_item_by_code(db: Session, item_code: str):
    normalized_code = normalize_item_code(item_code)
    stmt = (
        select(CollectionItem)
        .options(
            joinedload(CollectionItem.mineral).joinedload(MineralSpecies.chakras),
            joinedload(CollectionItem.mineral).joinedload(MineralSpecies.zodiac_signs),
            joinedload(CollectionItem.locality),
            joinedload(CollectionItem.images),
        )
        .where(CollectionItem.item_code == normalized_code)
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def delete_collection_item(db: Session, item: CollectionItem) -> tuple[int, list[str]]:
    image_paths = [image.file_path for image in list(item.images)]
    db.delete(item)
    db.commit()
    return delete_uploaded_images(image_paths)


def option_lists(db: Session) -> dict:
    minerals = db.execute(select(MineralSpecies.name).order_by(MineralSpecies.name)).scalars().all()
    countries = (
        db.execute(
            select(Locality.country)
            .where(Locality.country.is_not(None))
            .distinct()
            .order_by(Locality.country)
        )
        .scalars()
        .all()
    )
    chakras = db.execute(select(Chakra.name).order_by(Chakra.id)).scalars().all()
    return {
        "minerals": ["Todos"] + list(minerals),
        "countries": ["Todos"] + list(countries),
        "chakras": ["Todos"] + list(chakras),
        "item_types": list(ITEM_TYPE_FILTER_OPTIONS),
    }


def selected_item_type_from_label(label: str | None) -> str | None:
    return item_type_from_filter(label)
