from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.db import Base
from src.localities import (
    canonical_country,
    get_or_create_locality,
    has_locality_data,
    locality_coordinate_guess,
    locality_normalized_key,
    normalize_existing_localities,
    normalized_text_key,
)
from src.models import CollectionItem, Locality, MineralSpecies


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine, future=True)


def test_normalized_text_key_removes_accents_and_noise():
    assert normalized_text_key("  Los   Peñascales  ") == "los penascales"
    assert canonical_country("Espana") == "España"


def test_locality_normalized_key_collapses_equivalent_locations():
    first = locality_normalized_key(
        name="Colmenarejo",
        mine="Mina Antigua Pilar",
        region="Comunidad de Madrid",
        country="España",
    )
    second = locality_normalized_key(
        name=" colmenarejo ",
        mine="Mina   Antigua Pilar",
        region="Comunidad de Madrid",
        country="Espana",
    )

    assert first == second


def test_locality_normalized_key_prefers_mindat_locality_id():
    key = locality_normalized_key(
        mindat_locality_id="456",
        name="Nombre variable",
        country="España",
    )

    assert key == "mindat:456"
    assert has_locality_data(mindat_locality_id="456")


def test_get_or_create_locality_reuses_normalized_existing_row():
    db = make_session()
    first = get_or_create_locality(
        db,
        name="Colmenarejo",
        mine="Mina Antigua Pilar",
        region="Comunidad de Madrid",
        country="España",
    )
    db.flush()

    second = get_or_create_locality(
        db,
        name=" colmenarejo ",
        mine="Mina   Antigua Pilar",
        region="Comunidad de Madrid",
        country="Espana",
    )

    assert second.id == first.id
    assert db.execute(select(Locality)).scalars().all() == [first]


def test_get_or_create_locality_reuses_mindat_locality_id():
    db = make_session()
    first = get_or_create_locality(db, mindat_locality_id=456, name="Mina Antigua Pilar")
    db.flush()

    second = get_or_create_locality(
        db,
        mindat_locality_id="456",
        name="Texto distinto",
        country="España",
    )

    assert second.id == first.id
    assert second.country == "España"


def test_coordinate_guess_uses_known_locality_before_country():
    locality = Locality(name="Colmenarejo", region="Comunidad de Madrid", country="España")

    coordinate = locality_coordinate_guess(locality)

    assert coordinate is not None
    assert coordinate.note == "Aproximado por localidad"
    assert round(coordinate.latitude, 2) == 40.56


def test_normalize_existing_localities_merges_duplicates_and_reassigns_items():
    db = make_session()
    mineral = MineralSpecies(name="Quartz")
    first = Locality(
        name="Colmenarejo",
        mine="Mina Antigua Pilar",
        region="Comunidad de Madrid",
        country="Espana",
    )
    duplicate = Locality(
        name=" colmenarejo ",
        mine="Mina   Antigua Pilar",
        region="Comunidad de Madrid",
        country="España",
    )
    db.add_all([mineral, first, duplicate])
    db.flush()
    db.add_all(
        [
            CollectionItem(item_code="MIN-0001", mineral=mineral, locality=first, sold=False),
            CollectionItem(item_code="MIN-0002", mineral=mineral, locality=duplicate, sold=False),
        ]
    )
    db.commit()

    result = normalize_existing_localities(db)
    db.commit()

    localities = db.execute(select(Locality)).scalars().all()
    items = db.execute(select(CollectionItem).order_by(CollectionItem.item_code)).scalars().all()
    assert result["merged"] == 1
    assert result["reassigned_items"] == 1
    assert len(localities) == 1
    assert localities[0].country == "España"
    assert localities[0].normalized_key
    assert {item.locality_id for item in items} == {localities[0].id}


def test_normalize_existing_localities_merges_text_duplicate_into_mindat_row():
    db = make_session()
    mineral = MineralSpecies(name="Quartz")
    mindat_row = Locality(
        mindat_locality_id=456,
        name="Colmenarejo",
        mine="Mina Antigua Pilar",
        region="Comunidad de Madrid",
        country="España",
    )
    duplicate = Locality(
        name="Colmenarejo",
        mine="Mina Antigua Pilar",
        region="Comunidad de Madrid",
        country="Espana",
    )
    db.add_all([mineral, mindat_row, duplicate])
    db.flush()
    db.add_all(
        [
            CollectionItem(item_code="MIN-0001", mineral=mineral, locality=mindat_row, sold=False),
            CollectionItem(item_code="MIN-0002", mineral=mineral, locality=duplicate, sold=False),
        ]
    )
    db.commit()

    result = normalize_existing_localities(db)
    db.commit()

    localities = db.execute(select(Locality)).scalars().all()
    assert result["merged"] == 1
    assert len(localities) == 1
    assert localities[0].mindat_locality_id == 456
    assert localities[0].normalized_key == "mindat:456"
