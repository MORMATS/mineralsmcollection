from __future__ import annotations

from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload, Session

from src.models import CollectionItem, MineralSpecies, Locality, Chakra


def list_collection_items(
    db: Session,
    text: str | None = None,
    sold: bool | None = None,
    mineral_name: str | None = None,
    country: str | None = None,
    chakra: str | None = None,
):
    stmt = (
        select(CollectionItem)
        .options(
            joinedload(CollectionItem.mineral).joinedload(MineralSpecies.chakras),
            joinedload(CollectionItem.locality),
            joinedload(CollectionItem.images),
        )
        .join(CollectionItem.mineral)
        .outerjoin(CollectionItem.locality)
    )

    if text:
        like = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                CollectionItem.item_code.ilike(like),
                CollectionItem.display_name.ilike(like),
                MineralSpecies.name.ilike(like),
                CollectionItem.secondary_minerals.ilike(like),
                CollectionItem.special_features.ilike(like),
            )
        )

    if sold is not None:
        stmt = stmt.where(CollectionItem.sold == sold)

    if mineral_name and mineral_name != "Todos":
        stmt = stmt.where(MineralSpecies.name == mineral_name)

    if country and country != "Todos":
        stmt = stmt.where(Locality.country == country)

    if chakra and chakra != "Todos":
        stmt = stmt.join(MineralSpecies.chakras).where(Chakra.name == chakra)

    stmt = stmt.order_by(CollectionItem.created_at.desc())
    return db.execute(stmt).unique().scalars().all()


def get_item_by_code(db: Session, item_code: str):
    stmt = (
        select(CollectionItem)
        .options(
            joinedload(CollectionItem.mineral).joinedload(MineralSpecies.chakras),
            joinedload(CollectionItem.mineral).joinedload(MineralSpecies.zodiac_signs),
            joinedload(CollectionItem.locality),
            joinedload(CollectionItem.images),
        )
        .where(CollectionItem.item_code == item_code)
    )
    return db.execute(stmt).unique().scalar_one_or_none()


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
    }
