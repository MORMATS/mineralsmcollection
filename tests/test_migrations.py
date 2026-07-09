from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


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
    assert "normalized_key" in [column["name"] for column in inspector.get_columns("localities")]
    assert any(
        index["name"] == "ix_localities_normalized_key" and index["unique"]
        for index in inspector.get_indexes("localities")
    )


def test_locality_migration_deduplicates_existing_rows(monkeypatch, tmp_path):
    db_path = tmp_path / "migration-dedupe.db"
    database_url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "20260708_0004")

    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO mineral_species (id, name, updated_at)
                VALUES (1, 'Quartz', '2026-01-01 00:00:00')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO localities (id, name, mine, region, country)
                VALUES
                    (1, 'Colmenarejo', 'Mina Antigua Pilar', 'Comunidad de Madrid', 'Espana'),
                    (2, ' colmenarejo ', 'Mina   Antigua Pilar', 'Comunidad de Madrid', 'España')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO collection_items
                    (id, item_code, mineral_id, locality_id, sold, created_at, item_type)
                VALUES
                    (1, 'MIN-0001', 1, 1, 0, '2026-01-01 00:00:00', 'mineral'),
                    (2, 'MIN-0002', 1, 2, 0, '2026-01-01 00:00:00', 'mineral')
                """
            )
        )

    command.upgrade(cfg, "head")

    with engine.connect() as connection:
        locality_rows = connection.execute(text("SELECT id, country, normalized_key FROM localities")).all()
        item_locality_ids = connection.execute(
            text("SELECT DISTINCT locality_id FROM collection_items ORDER BY locality_id")
        ).scalars().all()

    assert len(locality_rows) == 1
    assert locality_rows[0].country == "España"
    assert locality_rows[0].normalized_key
    assert item_locality_ids == [locality_rows[0].id]
