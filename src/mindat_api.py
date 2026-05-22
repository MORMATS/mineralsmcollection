from __future__ import annotations

import json
import html
import re
from datetime import datetime
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import MineralSpecies
from src.settings import get_setting

MINDAT_BASE = "https://api.mindat.org/v1"


class MindatConfigError(RuntimeError):
    pass


def mindat_headers() -> dict:
    token = get_setting("MINDAT_API_KEY", "")
    if not token:
        raise MindatConfigError("MINDAT_API_KEY no esta configurado.")
    return {"Authorization": f"Token {token}"}


def _mindat_get(path: str, params: dict | None = None) -> Any:
    url = f"{MINDAT_BASE}{path}"
    resp = requests.get(url, headers=mindat_headers(), params=params, timeout=30)

    if resp.status_code in (401, 403):
        raise MindatConfigError("Mindat ha rechazado el token. Revisa MINDAT_API_KEY.")
    resp.raise_for_status()
    return resp.json()


def _clean_value(value: Any) -> Any:
    if value in (None, "", [], {}):
        return None
    return value


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_text(value: Any) -> str | None:
    value = _clean_value(value)
    if value is None:
        return None

    if isinstance(value, dict):
        for key in ("name", "title", "text", "value", "description", "formula"):
            if _clean_value(value.get(key)) is not None:
                return _to_text(value.get(key))
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    if isinstance(value, (list, tuple, set)):
        parts = [_to_text(item) for item in value]
        return ", ".join(part for part in parts if part)

    value = re.sub(r"<[^>]+>", "", str(value))
    return html.unescape(value).strip() or None


def _first(record: dict, *keys: str) -> Any:
    lowered = {str(key).lower(): value for key, value in record.items()}
    for key in keys:
        value = record.get(key)
        if value is None:
            value = lowered.get(key.lower())
        value = _clean_value(value)
        if value is not None:
            return value
    return None


def _first_text(record: dict, *keys: str) -> str | None:
    return _to_text(_first(record, *keys))


def _parse_decimal(text: str) -> float | None:
    text = (
        text.replace(",", ".")
        .replace("\u00bc", ".25")
        .replace("\u00bd", ".5")
        .replace("\u00be", ".75")
    )
    try:
        return float(text)
    except ValueError:
        return None


def _parse_hardness(value: Any) -> tuple[float | None, float | None]:
    value = _clean_value(value)
    if value is None:
        return None, None

    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed, parsed

    if isinstance(value, dict):
        lower = _first(value, "min", "minimum", "lower", "from", "hardness_min")
        upper = _first(value, "max", "maximum", "upper", "to", "hardness_max")
        if lower is not None or upper is not None:
            lower_float = _parse_decimal(str(lower)) if lower is not None else None
            upper_float = _parse_decimal(str(upper)) if upper is not None else None
            return lower_float, upper_float or lower_float
        value = _to_text(value)

    text = _to_text(value)
    if not text:
        return None, None

    numbers = [
        parsed
        for parsed in (_parse_decimal(match) for match in re.findall(r"\d+(?:[.,]\d+)?", text))
        if parsed is not None
    ]
    if not numbers:
        return None, None
    return min(numbers), max(numbers)


def _merge_records(summary: dict, detail: dict) -> dict:
    merged = dict(summary)
    for key, value in detail.items():
        if _clean_value(value) is not None:
            merged[key] = value
    return merged


def fetch_mindat_geomaterial_detail(record: dict) -> dict:
    """Fetch the detailed geomaterial record when Mindat exposes it."""
    mindat_id = _to_int(record.get("id") or record.get("mindat_id"))
    if not mindat_id:
        return record

    for path in (f"/geomaterials/{mindat_id}/", f"/minerals_ima/{mindat_id}/"):
        try:
            payload = _mindat_get(path)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (400, 404, 405):
                continue
            raise

        if isinstance(payload, dict):
            return _merge_records(record, payload)

    return record


def search_mindat_geomaterial(name: str) -> dict | None:
    """Search a geomaterial by name using Mindat API.

    The Mindat API can evolve, so the parser accepts both paginated and list payloads.
    """
    params = {"format": "json", "q": name}
    payload = _mindat_get("/geomaterials/", params=params)
    if isinstance(payload, dict):
        results = payload.get("results") or payload.get("data") or []
    elif isinstance(payload, list):
        results = payload
    else:
        results = []

    if not results:
        return None

    lowered = name.lower()
    exact = next((r for r in results if str(r.get("name", "")).lower() == lowered), None)
    return fetch_mindat_geomaterial_detail(exact or results[0])


def normalize_mindat_record(record: dict) -> dict:
    mindat_id = _to_int(record.get("id") or record.get("mindat_id"))
    source_url = _first_text(record, "url", "mindat_url", "source_url")
    if not source_url and mindat_id:
        source_url = f"https://www.mindat.org/min-{mindat_id}.html"

    hmin = _parse_decimal(str(_first(record, "hmin", "hardness_min", "hardness_lower") or ""))
    hmax = _parse_decimal(str(_first(record, "hmax", "hardness_max", "hardness_upper") or ""))
    hardness_min = hmin if hmin and hmin > 0 else None
    hardness_max = hmax if hmax and hmax > 0 else None
    parsed_min, parsed_max = _parse_hardness(
        _first(record, "hardness", "mohs_hardness", "mohs", "hardness_text")
    )
    if hardness_min is None:
        hardness_min = parsed_min if parsed_min and parsed_min > 0 else None
    if hardness_max is None:
        hardness_max = parsed_max if parsed_max and parsed_max > 0 else None

    return {
        "mindat_id": mindat_id,
        "rruff_id": _first_text(record, "rruff_id", "rruffid", "rruff"),
        "name": _first_text(record, "name", "title"),
        "formula": _first_text(
            record,
            "formula",
            "ima_formula",
            "mindat_formula",
            "chemistry",
            "chemical_formula",
        ),
        "category": _first_text(
            record,
            "category",
            "classification",
            "class",
            "ima_status",
            "entrytype_text",
            "group",
        ),
        "crystal_system": _first_text(
            record, "crystal_system", "crystal_system_name", "crystalsystem"
        ),
        "hardness_min": hardness_min,
        "hardness_max": hardness_max,
        "color": _first_text(
            record, "color", "colour", "colors", "colours", "commentcolor"
        ),
        "luster": _first_text(record, "luster", "lustre", "lustretype", "lustertype"),
        "streak": _first_text(record, "streak"),
        "description": _first_text(record, "description", "entrytype_text", "short_description"),
        "source_url": source_url,
        "api_raw_json": json.dumps(record, ensure_ascii=False),
    }


def upsert_mindat_mineral(db: Session, name: str) -> tuple[MineralSpecies | None, str]:
    record = search_mindat_geomaterial(name)
    if not record:
        return None, f"Sin resultados para {name}"

    data = normalize_mindat_record(record)
    mineral_name = data.get("name")
    if not mineral_name:
        return None, f"Mindat devolvio un registro sin nombre para {name}"

    mineral = None
    if data.get("mindat_id"):
        mineral = db.execute(
            select(MineralSpecies).where(MineralSpecies.mindat_id == data["mindat_id"])
        ).scalar_one_or_none()

    if mineral is None:
        mineral = db.execute(
            select(MineralSpecies).where(MineralSpecies.name == mineral_name)
        ).scalar_one_or_none()

    created = mineral is None
    if created:
        mineral = MineralSpecies(name=mineral_name)

    for field in [
        "mindat_id",
        "rruff_id",
        "formula",
        "category",
        "crystal_system",
        "hardness_min",
        "hardness_max",
        "color",
        "luster",
        "streak",
        "description",
        "source_url",
        "api_raw_json",
    ]:
        value = data.get(field)
        if value not in (None, ""):
            setattr(mineral, field, value)

    mineral.updated_at = datetime.utcnow()
    db.add(mineral)
    db.commit()
    db.refresh(mineral)

    action = "creado" if created else "actualizado"
    return mineral, f"{mineral.name} {action}"
