from __future__ import annotations

import json
from datetime import datetime
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


def search_mindat_geomaterial(name: str) -> dict | None:
    """Search a geomaterial by name using Mindat API.

    The Mindat API can evolve, so the parser accepts both paginated and list payloads.
    """
    url = f"{MINDAT_BASE}/geomaterials/"
    params = {"format": "json", "q": name}
    resp = requests.get(url, headers=mindat_headers(), params=params, timeout=30)

    if resp.status_code in (401, 403):
        raise MindatConfigError("Mindat ha rechazado el token. Revisa MINDAT_API_KEY.")
    resp.raise_for_status()

    payload = resp.json()
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
    return exact or results[0]


def normalize_mindat_record(record: dict) -> dict:
    mindat_id = record.get("id")
    source_url = record.get("url")
    if not source_url and mindat_id:
        source_url = f"https://www.mindat.org/min-{mindat_id}.html"

    return {
        "mindat_id": mindat_id,
        "name": record.get("name") or record.get("title"),
        "formula": record.get("formula") or record.get("ima_formula") or record.get("chemistry"),
        "crystal_system": record.get("crystal_system") or record.get("crystal_system_name"),
        "description": record.get("description") or record.get("entrytype_text"),
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
        "formula",
        "crystal_system",
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
