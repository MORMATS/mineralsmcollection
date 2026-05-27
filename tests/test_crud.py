from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from src import image_utils
from src.crud import (
    delete_collection_item,
    generate_next_item_code,
    get_item_by_code,
    normalize_item_code,
)
from src.db import Base
from src.models import CollectionItem, ItemImage, MineralSpecies


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


def test_delete_collection_item_removes_database_rows_and_files(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(image_utils, "UPLOAD_DIR", upload_dir)
    image_dir = upload_dir / "min-0001"
    image_dir.mkdir(parents=True)
    image_path = image_dir / "min-0001-1.webp"
    image_path.write_bytes(b"fake image")

    db = make_session()
    mineral = MineralSpecies(name="Quartz")
    item = CollectionItem(item_code="MIN-0001", mineral=mineral, sold=False)
    item.images.append(
        ItemImage(
            file_path=str(image_path.relative_to(upload_dir.parent)),
            is_cover=True,
            sort_order=1,
        )
    )
    db.add(item)
    db.commit()
    item_id = item.id

    deleted_count, failures = delete_collection_item(db, item)

    assert deleted_count == 1
    assert failures == []
    assert db.get(CollectionItem, item_id) is None
    assert db.execute(select(ItemImage)).scalars().all() == []
    assert not image_path.exists()
    assert not image_dir.exists()
