from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.db import get_session
from src.mindat_api import upsert_mindat_mineral


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--names", required=True, help="Comma-separated mineral names")
    args = parser.parse_args()

    db = get_session()
    try:
        for name in [n.strip() for n in args.names.split(",") if n.strip()]:
            mineral, message = upsert_mindat_mineral(db, name)
            print(message)
    finally:
        db.close()


if __name__ == "__main__":
    main()
