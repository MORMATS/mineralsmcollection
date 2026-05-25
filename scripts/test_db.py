from pathlib import Path
import sys
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.db import get_engine, get_database_url, redact_url


def main():
    print(f"DATABASE_URL={redact_url(get_database_url())}")
    engine = get_engine()
    with engine.connect() as conn:
        version = conn.execute(text("select version()")).scalar_one()
        print(version)
    print("DB connection OK.")


if __name__ == "__main__":
    main()
