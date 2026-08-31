from __future__ import annotations

from src.localities import clean_location_text, normalized_locality_values


class LocalityValidationError(ValueError):
    pass


def _optional_positive_int(value: object, label: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError as exc:
        raise LocalityValidationError(f"{label} debe ser un número entero.") from exc
    if parsed <= 0:
        raise LocalityValidationError(f"{label} debe ser mayor que cero.")
    return parsed


def _optional_float(value: object, label: str) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise LocalityValidationError(f"{label} debe ser un número válido.") from exc


def parse_locality_form(
    *,
    mindat_locality_id: object = None,
    name: object = None,
    mine: object = None,
    region: object = None,
    country: object = None,
    latitude: object = None,
    longitude: object = None,
    source_url: object = None,
    notes: object = None,
) -> dict[str, object]:
    mindat_id = _optional_positive_int(mindat_locality_id, "El ID de Mindat")
    latitude_value = _optional_float(latitude, "La latitud")
    longitude_value = _optional_float(longitude, "La longitud")

    if (latitude_value is None) != (longitude_value is None):
        raise LocalityValidationError("Indica latitud y longitud juntas, o deja ambas vacías.")
    if latitude_value is not None and not -90 <= latitude_value <= 90:
        raise LocalityValidationError("La latitud debe estar entre -90 y 90.")
    if longitude_value is not None and not -180 <= longitude_value <= 180:
        raise LocalityValidationError("La longitud debe estar entre -180 y 180.")

    values = normalized_locality_values(
        mindat_locality_id=mindat_id,
        name=name,
        mine=mine,
        region=region,
        country=country,
        latitude=latitude_value,
        longitude=longitude_value,
    )
    if values["normalized_key"] is None:
        raise LocalityValidationError(
            "Añade al menos un nombre, mina, región, país, ID de Mindat o coordenadas."
        )

    values["source_url"] = clean_location_text(source_url)
    values["notes"] = clean_location_text(notes)
    return values
