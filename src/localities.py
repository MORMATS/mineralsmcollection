from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Locality


COUNTRY_CENTROIDS = {
    "afganistan": (33.9391, 67.71),
    "afghanistan": (33.9391, 67.71),
    "alemania": (51.1657, 10.4515),
    "argentina": (-38.4161, -63.6167),
    "australia": (-25.2744, 133.7751),
    "bolivia": (-16.2902, -63.5887),
    "brasil": (-14.235, -51.9253),
    "brazil": (-14.235, -51.9253),
    "canada": (56.1304, -106.3468),
    "chile": (-35.6751, -71.543),
    "china": (35.8617, 104.1954),
    "colombia": (4.5709, -74.2973),
    "congo": (-4.0383, 21.7587),
    "czech republic": (49.8175, 15.473),
    "democratic republic of congo": (-4.0383, 21.7587),
    "egipto": (26.8206, 30.8025),
    "egypt": (26.8206, 30.8025),
    "espana": (40.4637, -3.7492),
    "estados unidos": (39.8283, -98.5795),
    "finland": (61.9241, 25.7482),
    "finlandia": (61.9241, 25.7482),
    "france": (46.2276, 2.2137),
    "francia": (46.2276, 2.2137),
    "germany": (51.1657, 10.4515),
    "greece": (39.0742, 21.8243),
    "grecia": (39.0742, 21.8243),
    "india": (20.5937, 78.9629),
    "italia": (41.8719, 12.5674),
    "italy": (41.8719, 12.5674),
    "japan": (36.2048, 138.2529),
    "japon": (36.2048, 138.2529),
    "madagascar": (-18.7669, 46.8691),
    "marruecos": (31.7917, -7.0926),
    "mexico": (23.6345, -102.5528),
    "morocco": (31.7917, -7.0926),
    "mozambique": (-18.6657, 35.5296),
    "myanmar": (21.9162, 95.956),
    "namibia": (-22.9576, 18.4904),
    "noruega": (60.472, 8.4689),
    "norway": (60.472, 8.4689),
    "pakistan": (30.3753, 69.3451),
    "peru": (-9.19, -75.0152),
    "poland": (51.9194, 19.1451),
    "polonia": (51.9194, 19.1451),
    "portugal": (39.3999, -8.2245),
    "reino unido": (55.3781, -3.436),
    "romania": (45.9432, 24.9668),
    "rumania": (45.9432, 24.9668),
    "russia": (61.524, 105.3188),
    "south africa": (-30.5595, 22.9375),
    "spain": (40.4637, -3.7492),
    "sri lanka": (7.8731, 80.7718),
    "sudafrica": (-30.5595, 22.9375),
    "sweden": (60.1282, 18.6435),
    "suecia": (60.1282, 18.6435),
    "tanzania": (-6.369, 34.8888),
    "turkey": (38.9637, 35.2433),
    "turquia": (38.9637, 35.2433),
    "united kingdom": (55.3781, -3.436),
    "united states": (39.8283, -98.5795),
    "usa": (39.8283, -98.5795),
}

COUNTRY_LABELS = {
    "espana": "España",
    "spain": "España",
    "marruecos": "Marruecos",
    "morocco": "Marruecos",
    "mexico": "México",
    "japon": "Japón",
    "turquia": "Turquía",
    "sudafrica": "Sudáfrica",
    "reino unido": "Reino Unido",
    "united kingdom": "Reino Unido",
    "estados unidos": "Estados Unidos",
    "united states": "Estados Unidos",
    "usa": "Estados Unidos",
}

PLACE_CENTROIDS = {
    ("espana", "comunidad de madrid"): (40.4168, -3.7038, "Aproximado por region"),
    ("espana", "colmenarejo"): (40.5606, -4.0171, "Aproximado por localidad"),
    ("espana", "los penascales"): (40.5712, -3.9277, "Aproximado por localidad"),
    ("marruecos", "atlas medio"): (32.6, -5.4, "Aproximado por region"),
    ("marruecos", "marrakech"): (31.6295, -7.9811, "Aproximado por localidad"),
}


@dataclass(frozen=True)
class CoordinateGuess:
    latitude: float
    longitude: float
    note: str


def clean_location_text(value: object) -> str | None:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def normalized_text_key(value: object) -> str:
    text = clean_location_text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_country(value: object) -> str | None:
    text = clean_location_text(value)
    if not text:
        return None
    return COUNTRY_LABELS.get(normalized_text_key(text), text)


def valid_coordinate(latitude: object, longitude: object) -> bool:
    if latitude is None or longitude is None:
        return False
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def has_locality_data(
    name: object = None,
    mine: object = None,
    region: object = None,
    country: object = None,
    latitude: object = None,
    longitude: object = None,
) -> bool:
    return any(clean_location_text(value) for value in (name, mine, region, country)) or valid_coordinate(
        latitude,
        longitude,
    )


def locality_normalized_key(
    *,
    name: object = None,
    mine: object = None,
    region: object = None,
    country: object = None,
    latitude: object = None,
    longitude: object = None,
) -> str | None:
    country_value = canonical_country(country)
    text_parts = {
        "country": normalized_text_key(country_value),
        "region": normalized_text_key(region),
        "mine": normalized_text_key(mine),
        "name": normalized_text_key(name),
    }
    if any(text_parts.values()):
        return "|".join(f"{field}:{value}" for field, value in text_parts.items())

    if valid_coordinate(latitude, longitude):
        return f"coords:{float(latitude):.5f},{float(longitude):.5f}"

    return None


def normalized_locality_values(
    *,
    name: object = None,
    mine: object = None,
    region: object = None,
    country: object = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, object]:
    clean_name = clean_location_text(name)
    clean_mine = clean_location_text(mine)
    clean_region = clean_location_text(region)
    clean_country = canonical_country(country)
    normalized_key = locality_normalized_key(
        name=clean_name,
        mine=clean_mine,
        region=clean_region,
        country=clean_country,
        latitude=latitude,
        longitude=longitude,
    )
    return {
        "name": clean_name,
        "mine": clean_mine,
        "region": clean_region,
        "country": clean_country,
        "latitude": latitude,
        "longitude": longitude,
        "normalized_key": normalized_key,
    }


def locality_label(locality: Locality | None) -> str:
    if not locality:
        return "Origen por completar"
    parts = [locality.name, locality.mine, locality.region, locality.country]
    return " · ".join(part for part in parts if clean_location_text(part)) or "Origen por completar"


def locality_coordinate_guess(locality: Locality | None) -> CoordinateGuess | None:
    if not locality:
        return None

    if valid_coordinate(locality.latitude, locality.longitude):
        return CoordinateGuess(float(locality.latitude), float(locality.longitude), "Coordenada exacta")

    country_key = normalized_text_key(locality.country)
    for value in (locality.name, locality.mine, locality.region):
        place_key = normalized_text_key(value)
        if not place_key:
            continue
        centroid = PLACE_CENTROIDS.get((country_key, place_key))
        if centroid:
            latitude, longitude, note = centroid
            return CoordinateGuess(latitude, longitude, note)

    centroid = COUNTRY_CENTROIDS.get(country_key)
    if centroid:
        latitude, longitude = centroid
        return CoordinateGuess(latitude, longitude, "Aproximado por pais")

    return None


def _apply_values(locality: Locality, values: dict[str, object]) -> bool:
    changed = False
    for field in ("name", "mine", "region", "country", "normalized_key"):
        value = values.get(field)
        if getattr(locality, field) != value and (value or not getattr(locality, field)):
            setattr(locality, field, value)
            changed = True

    for field in ("latitude", "longitude"):
        value = values.get(field)
        if getattr(locality, field) is None and value is not None:
            setattr(locality, field, value)
            changed = True

    return changed


def get_or_create_locality(
    db: Session,
    *,
    name: object = None,
    mine: object = None,
    region: object = None,
    country: object = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Locality | None:
    if not has_locality_data(name, mine, region, country, latitude, longitude):
        return None

    values = normalized_locality_values(
        name=name,
        mine=mine,
        region=region,
        country=country,
        latitude=latitude,
        longitude=longitude,
    )
    normalized_key = values.get("normalized_key")
    locality = None
    if normalized_key:
        locality = db.execute(
            select(Locality).where(Locality.normalized_key == normalized_key)
        ).scalar_one_or_none()

    if locality:
        _apply_values(locality, values)
        return locality

    locality = Locality(**values)
    db.add(locality)
    return locality


def _locality_score(locality: Locality) -> tuple[int, int, int]:
    has_coordinates = int(valid_coordinate(locality.latitude, locality.longitude))
    filled_fields = sum(
        1 for value in (locality.country, locality.region, locality.mine, locality.name) if clean_location_text(value)
    )
    return has_coordinates, filled_fields, -int(locality.id or 0)


def normalize_existing_localities(db: Session) -> dict[str, int]:
    localities = db.execute(select(Locality).order_by(Locality.id)).scalars().all()
    groups: dict[str, list[tuple[Locality, dict[str, object]]]] = {}
    updated = 0

    for locality in localities:
        values = normalized_locality_values(
            name=locality.name,
            mine=locality.mine,
            region=locality.region,
            country=locality.country,
            latitude=locality.latitude,
            longitude=locality.longitude,
        )
        normalized_key = values.get("normalized_key")
        if normalized_key:
            groups.setdefault(str(normalized_key), []).append((locality, values))
        elif _apply_values(locality, values):
            updated += 1

    merged = 0
    reassigned_items = 0
    for group_entries in groups.values():
        group = [locality for locality, _ in group_entries]
        if len(group) < 2:
            locality, values = group_entries[0]
            if _apply_values(locality, values):
                updated += 1
            continue

        canonical = max(group, key=_locality_score)
        canonical_values = next(values for locality, values in group_entries if locality is canonical)
        for duplicate in group:
            if duplicate is canonical:
                continue
            with db.no_autoflush:
                duplicate_items = list(duplicate.items)
            reassigned_items += len(duplicate_items)
            for item in duplicate_items:
                item.locality = canonical
            duplicate.normalized_key = None
            db.delete(duplicate)
            merged += 1
        if _apply_values(canonical, canonical_values):
            updated += 1

    return {"updated": updated, "merged": merged, "reassigned_items": reassigned_items}
