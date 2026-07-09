from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_initial_migration_creates_schema(monkeypatch, tmp_path):
    db_path = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(f"sqlite:///{db_path.as_posix()}", future=True))
    tables = set(inspector.get_table_names())

    assert "alembic_version" in tables
    assert "collection_items" in tables
    assert "mineral_species" in tables
    assert "item_images" in tables
    assert "sort_order" in [column["name"] for column in inspector.get_columns("item_images")]
    assert "item_type" in [column["name"] for column in inspector.get_columns("collection_items")]
