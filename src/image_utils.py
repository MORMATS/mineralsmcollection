from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image, UnidentifiedImageError

from src.db import UPLOAD_DIR
from src.settings import get_int_setting


MAX_UPLOAD_MB = get_int_setting("IMAGE_MAX_UPLOAD_MB", 10)
MAX_IMAGE_PIXELS = get_int_setting("IMAGE_MAX_PIXELS", 20_000_000)
THUMBNAIL_SIZE = (
    get_int_setting("IMAGE_MAX_WIDTH", 1600),
    get_int_setting("IMAGE_MAX_HEIGHT", 1600),
)
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageUploadError(ValueError):
    pass


def safe_slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "item"


def resolve_uploaded_path(file_path: str) -> Path | None:
    storage_root = UPLOAD_DIR.parent.resolve()
    upload_root = UPLOAD_DIR.resolve()
    path = (storage_root / file_path).resolve()
    try:
        path.relative_to(upload_root)
    except ValueError:
        return None
    return path


def delete_uploaded_images(file_paths: Iterable[str]) -> tuple[int, list[str]]:
    deleted_count = 0
    failures: list[str] = []
    parent_dirs: set[Path] = set()
    upload_root = UPLOAD_DIR.resolve()

    for file_path in file_paths:
        path = resolve_uploaded_path(file_path)
        if path is None:
            failures.append(f"{file_path}: ruta fuera de la carpeta de subidas")
            continue

        parent_dirs.add(path.parent)
        try:
            if path.exists():
                path.unlink()
                deleted_count += 1
        except OSError as exc:
            failures.append(f"{file_path}: {exc}")

    for parent_dir in sorted(parent_dirs, key=lambda path: len(path.parts), reverse=True):
        try:
            parent_dir.relative_to(upload_root)
        except ValueError:
            continue

        try:
            parent_dir.rmdir()
        except OSError:
            pass

    return deleted_count, failures


def save_uploaded_images(item_code: str, uploaded_files, start_index: int = 0) -> list[str]:
    paths: list[str] = []
    item_dir = UPLOAD_DIR / safe_slug(item_code)
    item_dir.mkdir(parents=True, exist_ok=True)

    try:
        for index, uploaded in enumerate(uploaded_files or [], start=start_index + 1):
            content = bytes(uploaded.getbuffer())
            max_bytes = MAX_UPLOAD_MB * 1024 * 1024
            if len(content) > max_bytes:
                raise ImageUploadError(f"{uploaded.name} supera el limite de {MAX_UPLOAD_MB} MB.")

            try:
                with Image.open(BytesIO(content)) as probe:
                    image_format = probe.format
                    width, height = probe.size
                    probe.verify()
            except (UnidentifiedImageError, OSError) as exc:
                raise ImageUploadError(f"{uploaded.name} no es una imagen valida.") from exc

            if image_format not in ALLOWED_FORMATS:
                raise ImageUploadError(f"{uploaded.name} usa un formato no permitido.")
            if width * height > MAX_IMAGE_PIXELS:
                raise ImageUploadError(f"{uploaded.name} tiene demasiados pixeles.")

            dest = item_dir / f"{safe_slug(item_code)}-{index}.webp"
            with Image.open(BytesIO(content)) as img:
                img.thumbnail(THUMBNAIL_SIZE)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                with NamedTemporaryFile("wb", dir=item_dir, delete=False, suffix=".tmp") as tmp:
                    tmp_path = Path(tmp.name)
                    img.save(tmp, format="WEBP", quality=88, method=6)

            tmp_path.replace(dest)
            paths.append(str(dest.relative_to(UPLOAD_DIR.parent)))
    except Exception:
        for saved_path in paths:
            try:
                (UPLOAD_DIR.parent / saved_path).unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return paths
