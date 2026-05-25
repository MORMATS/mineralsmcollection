from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.db import get_engine, get_session
from src.seeds import seed_all


def migrate_database(alembic_cfg: Config) -> None:
    engine = get_engine()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "collection_items" in tables and "alembic_version" not in tables:
        command.stamp(alembic_cfg, "20260525_0001")

    command.upgrade(alembic_cfg, "head")


def main():
    alembic_cfg = Config(str(ROOT / "alembic.ini"))
    migrate_database(alembic_cfg)

    db = get_session()
    try:
        seed_all(db)
        print("Database migrated and seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
