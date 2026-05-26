from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.crud import generate_next_item_code, get_item_by_code, normalize_item_code
from src.db import Base
from src.models import CollectionItem, MineralSpecies


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine, future=True)


def test_generate_next_item_code_skips_existing_codes():
    db = make_session()
    mineral = MineralSpecies(name="Quartz")
    db.add(mineral)
    db.flush()
    db.add_all(
        [
            CollectionItem(item_code="MIN-0001", mineral=mineral, sold=False),
            CollectionItem(item_code="MIN-0004", mineral=mineral, sold=False),
            CollectionItem(item_code="ABC-9999", mineral=mineral, sold=False),
        ]
    )
    db.commit()

    assert generate_next_item_code(db) == "MIN-0005"


def test_normalize_item_code_accepts_bare_number():
    assert normalize_item_code("12") == "MIN-0012"
    assert normalize_item_code("min-12") == "MIN-0012"


def test_get_item_by_code_accepts_bare_number():
    db = make_session()
    mineral = MineralSpecies(name="Quartz")
    db.add(mineral)
    db.flush()
    db.add(CollectionItem(item_code="MIN-0012", mineral=mineral, sold=False))
    db.commit()

    assert get_item_by_code(db, "12").item_code == "MIN-0012"
