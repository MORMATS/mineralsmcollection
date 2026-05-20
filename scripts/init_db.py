from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.db import init_db, get_session
from src.seeds import seed_all


def main():
    init_db()
    db = get_session()
    try:
        seed_all(db)
        print("Database initialized and seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
