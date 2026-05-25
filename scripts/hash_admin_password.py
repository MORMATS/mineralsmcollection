from __future__ import annotations

from getpass import getpass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.auth import hash_admin_password


def main() -> None:
    password = getpass("Admin password: ")
    confirm = getpass("Repeat admin password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    if len(password) < 8:
        raise SystemExit("Use at least 8 characters.")

    print(hash_admin_password(password))


if __name__ == "__main__":
    main()
