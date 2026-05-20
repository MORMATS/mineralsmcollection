from __future__ import annotations

import re
from pathlib import Path
from PIL import Image

from src.db import UPLOAD_DIR


def safe_slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "item"


def save_uploaded_images(item_code: str, uploaded_files) -> list[str]:
    paths: list[str] = []
    item_dir = UPLOAD_DIR / safe_slug(item_code)
    item_dir.mkdir(parents=True, exist_ok=True)

    for index, uploaded in enumerate(uploaded_files or []):
        suffix = Path(uploaded.name).suffix.lower() or ".jpg"
        dest = item_dir / f"{safe_slug(item_code)}-{index + 1}{suffix}"
        with dest.open("wb") as f:
            f.write(uploaded.getbuffer())

        try:
            with Image.open(dest) as img:
                img.thumbnail((1600, 1600))
                img.save(dest)
        except Exception:
            pass

        paths.append(str(dest.relative_to(UPLOAD_DIR.parent)))

    return paths
