from __future__ import annotations

import html
import json
import re
from typing import Any

from src.models import MineralSpecies


CURATED_RAW_KEYS = {
    "aboutname",
    "category",
    "chemistry",
    "chemical_formula",
    "class",
    "classification",
    "color",
    "colour",
    "colours",
    "colors",
    "commentcolor",
    "crystal_system",
    "crystal_system_name",
    "crystalsystem",
    "description",
    "elements",
    "entrytype_text",
    "formula",
    "group",
    "hardness",
    "hardness_lower",
    "hardness_max",
    "hardness_min",
    "hardness_text",
    "hardness_upper",
    "hmax",
    "hmin",
    "id",
    "ima_formula",
    "ima_status",
    "lustre",
    "lustretype",
    "lustertype",
    "luster",
    "mindat_formula",
    "mindat_id",
    "mindat_url",
    "mohs",
    "mohs_hardness",
    "name",
    "otheroccurrence",
    "rruff",
    "rruff_id",
    "rruffid",
    "short_description",
    "sigelements",
    "source_url",
    "streak",
    "title",
    "updttime",
    "url",
    "varietyof",
}

NOISE_KEYS = {
    "a",
    "b",
    "c",
    "alpha",
    "beta",
    "gamma",
    "cclass",
    "csmetamict",
    "entrytype",
    "groupid",
    "guid",
    "hardtype",
    "longid",
    "nolocadd",
    "polytypeof",
    "publication_year",
    "rock_parent",
    "rock_parent2",
    "rock_root",
    "spacegroup",
    "spacegroupset",
    "synid",
    "weighting",
    "z",
}

RAW_LABELS = {
    "cleavage": "Exfoliacion",
    "dana": "Clasificacion Dana",
    "dana8": "Clasificacion Dana",
    "density": "Densidad",
    "diaphaneity": "Diafanidad",
    "fracture": "Fractura",
    "habit": "Habito cristalino",
    "ima_symbol": "Simbolo IMA",
    "optical": "Datos opticos",
    "optical_data": "Datos opticos",
    "paragenesis": "Paragenesis",
    "photos": "Fotos",
    "relations": "Relaciones",
    "specific_gravity": "Gravedad especifica",
    "strunz": "Clasificacion Strunz",
    "synonyms": "Sinonimos",
    "tenacity": "Tenacidad",
    "transparency": "Transparencia",
    "varieties": "Variedades",
}


TERM_TRANSLATIONS = {
    "adamantine": "adamantino",
    "aggregate": "agregado",
    "amorphous": "amorfo",
    "black": "negro",
    "blue": "azul",
    "brown": "marron",
    "carbonate": "carbonato",
    "carbonates": "carbonatos",
    "colorless": "incoloro",
    "colourless": "incoloro",
    "cubic": "cubico",
    "dull": "mate",
    "earthy": "terroso",
    "fluorescent": "fluorescente",
    "gray": "gris",
    "green": "verde",
    "grey": "gris",
    "hexagonal": "hexagonal",
    "isometric": "isometrico",
    "metallic": "metalico",
    "mineral": "mineral",
    "monoclinic": "monoclinico",
    "nonmetallic": "no metalico",
    "opaque": "opaco",
    "orange": "naranja",
    "orthorhombic": "ortorrombico",
    "oxide": "oxido",
    "oxides": "oxidos",
    "pearly": "nacarado",
    "pink": "rosa",
    "purple": "morado",
    "red": "rojo",
    "resinous": "resinoso",
    "silicate": "silicato",
    "silicates": "silicatos",
    "sulfate": "sulfato",
    "sulfates": "sulfatos",
    "sulphate": "sulfato",
    "sulphates": "sulfatos",
    "tetragonal": "tetragonal",
    "translucent": "traslucido",
    "transparent": "transparente",
    "triclinic": "triclinico",
    "trigonal": "trigonal",
    "vitreous": "vitreo",
    "white": "blanco",
    "yellow": "amarillo",
}


def translate_mindat_text(value: str) -> str:
    text = value.strip()
    if not text or len(text) > 220 or "://" in text:
        return value

    normalized = re.sub(r"\s+", " ", text.lower())
    if normalized in TERM_TRANSLATIONS:
        return TERM_TRANSLATIONS[normalized]

    parts = re.split(r"([,;/()])", text)
    changed = False
    translated_parts = []
    for part in parts:
        key = re.sub(r"\s+", " ", part.strip().lower())
        translated = TERM_TRANSLATIONS.get(key)
        if translated:
            prefix = part[: len(part) - len(part.lstrip())]
            suffix = part[len(part.rstrip()) :]
            translated_parts.append(f"{prefix}{translated}{suffix}")
            changed = True
        else:
            translated_parts.append(part)

    if changed:
        return "".join(translated_parts)

    result = text
    for english, spanish in sorted(TERM_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        result = re.sub(rf"\b{re.escape(english)}\b", spanish, result, flags=re.IGNORECASE)

    return result


def load_mindat_raw(mineral: MineralSpecies) -> dict:
    if not mineral.api_raw_json:
        return {}
    try:
        payload = json.loads(mineral.api_raw_json)
    except json.JSONDecodeError:
        return {"api_raw_json": mineral.api_raw_json}
    return payload if isinstance(payload, dict) else {"datos": payload}


def normalize_key(key: str) -> str:
    return str(key).strip().lower()


def raw_get(raw: dict, *keys: str) -> Any:
    lowered = {normalize_key(key): value for key, value in raw.items()}
    for key in keys:
        value = lowered.get(normalize_key(key))
        if not is_blank(value):
            return value
    return None


def strip_html(value: str) -> str:
    cleaned = re.sub(r"<\s*sub\s*>", "", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*/\s*sub\s*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*sup\s*>", "^", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*/\s*sup\s*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def is_zeroish(value: Any) -> bool:
    if isinstance(value, bool):
        return value is False
    if isinstance(value, (int, float)):
        return float(value) == 0
    if isinstance(value, str):
        return value.strip() in {"0", "0.0", "0.00", "false", "False"}
    return False


def is_blank(value: Any) -> bool:
    return value in (None, "", [], {})


def format_value(value: Any) -> str:
    if is_blank(value):
        return ""

    if isinstance(value, dict):
        for key in ("name", "title", "text", "value", "description", "formula"):
            nested = format_value(value.get(key))
            if nested:
                return nested
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)

    if isinstance(value, list):
        parts = [format_value(item) for item in value]
        return ", ".join(part for part in parts if part)

    return strip_html(str(value))


def first_text(raw: dict, *keys: str) -> str:
    return translate_mindat_text(format_value(raw_get(raw, *keys)))


def first_positive_number(raw: dict, *keys: str) -> float | None:
    value = raw_get(raw, *keys)
    if is_blank(value):
        return None
    try:
        parsed = float(str(value).replace(",", "."))
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def mineral_formula(mineral: MineralSpecies, raw: dict) -> str:
    return format_value(mineral.formula) or first_text(
        raw, "mindat_formula", "formula", "ima_formula", "chemistry", "chemical_formula"
    )


def mineral_elements(mineral: MineralSpecies, raw: dict) -> str:
    return format_value(mineral.elements) or first_text(raw, "elements", "sigelements")


def mineral_category(mineral: MineralSpecies, raw: dict) -> str:
    return mineral.category or first_text(
        raw, "category", "classification", "class", "ima_status", "entrytype_text", "group"
    )


def mineral_color(mineral: MineralSpecies, raw: dict) -> str:
    base = mineral.color or first_text(raw, "color", "colour", "colors", "colours")
    comment = first_text(raw, "commentcolor")
    if base and comment and comment.lower() not in base.lower():
        return f"{base}. {comment}"
    return base or comment


def mineral_luster(mineral: MineralSpecies, raw: dict) -> str:
    return mineral.luster or first_text(raw, "luster", "lustre", "lustretype", "lustertype")


def mineral_hardness(mineral: MineralSpecies, raw: dict) -> str:
    lower = mineral.hardness_min or first_positive_number(raw, "hmin", "hardness_min")
    upper = mineral.hardness_max or first_positive_number(raw, "hmax", "hardness_max")
    if lower and upper:
        return f"{lower:g}" if lower == upper else f"{lower:g} - {upper:g}"
    if lower:
        return f"{lower:g}"
    if upper:
        return f"{upper:g}"
    return first_text(raw, "hardness", "mohs_hardness", "mohs", "hardness_text")


def mineral_description(mineral: MineralSpecies) -> str:
    raw = load_mindat_raw(mineral)
    return mineral.description or first_text(raw, "description", "short_description")


def mineral_wiki_sections(mineral: MineralSpecies) -> dict[str, list[tuple[str, str]]]:
    raw = load_mindat_raw(mineral)
    source_url = mineral.source_url or first_text(raw, "url", "mindat_url", "source_url")
    if not source_url and mineral.mindat_id:
        source_url = f"https://www.mindat.org/min-{mineral.mindat_id}.html"

    sections = {
        "Identificacion": [
            ("Nombre", mineral.name),
            ("ID Mindat", str(mineral.mindat_id or first_text(raw, "id") or "")),
            ("ID RRUFF", mineral.rruff_id or first_text(raw, "rruff_id", "rruffid", "rruff")),
            ("Fuente", source_url),
        ],
        "Quimica y clasificacion": [
            ("Fórmula", mineral_formula(mineral, raw)),
            ("Elementos", mineral_elements(mineral, raw)),
            ("Categoría", mineral_category(mineral, raw)),
            ("Sistema cristalino", mineral.crystal_system or first_text(raw, "crystal_system")),
            ("Variedad de", first_text(raw, "varietyof")),
        ],
        "Propiedades visibles": [
            ("Color", mineral_color(mineral, raw)),
            ("Brillo", mineral_luster(mineral, raw)),
            ("Raya", mineral.streak or first_text(raw, "streak")),
            ("Dureza Mohs", mineral_hardness(mineral, raw)),
        ],
        "Contexto": [
            ("Origen del nombre", first_text(raw, "aboutname")),
            ("Ambientes y ocurrencias", first_text(raw, "otheroccurrence")),
            ("Actualizado en Mindat", first_text(raw, "updttime")),
        ],
    }
    return {
        title: [(label, value) for label, value in rows if value]
        for title, rows in sections.items()
    }


def mineral_wiki_rows(mineral: MineralSpecies) -> list[tuple[str, str]]:
    rows = []
    for section_rows in mineral_wiki_sections(mineral).values():
        rows.extend(section_rows)
    return rows


def humanize_key(key: str) -> str:
    normalized = normalize_key(key)
    if normalized in RAW_LABELS:
        return RAW_LABELS[normalized]
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", str(key)).replace("_", " ")
    return spaced.strip().capitalize()


def should_hide_extra(key: str, value: Any) -> bool:
    normalized = normalize_key(key)
    if normalized in CURATED_RAW_KEYS or normalized in NOISE_KEYS:
        return True
    if normalized.endswith("error") or "error" in normalized:
        return True
    if re.match(r"^(dana8ed|strunz10ed|vhn|optical|dcalc|dmeas|va3)", normalized):
        return True
    if is_zeroish(value):
        return True
    return False


def extra_mindat_rows(mineral: MineralSpecies) -> list[tuple[str, str]]:
    raw = load_mindat_raw(mineral)
    rows = []
    for key in sorted(raw):
        value = raw[key]
        if should_hide_extra(key, value):
            continue
        formatted = format_value(value)
        if formatted:
            rows.append((humanize_key(key), translate_mindat_text(formatted)))
    return rows
