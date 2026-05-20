from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Chakra, ZodiacSign, MineralSpecies, Locality, CollectionItem


CHAKRAS = [
    ("Raiz", "Rojo", "Tierra", "Estabilidad, seguridad y enraizamiento."),
    ("Sacro", "Naranja", "Agua", "Creatividad, sensualidad y flujo emocional."),
    ("Plexo solar", "Amarillo", "Fuego", "Voluntad, confianza y accion."),
    ("Corazon", "Verde/Rosa", "Aire", "Amor, compasion y equilibrio."),
    ("Garganta", "Azul", "Eter", "Comunicacion y expresion."),
    ("Tercer ojo", "Indigo", "Luz", "Intuicion y claridad mental."),
    ("Corona", "Violeta/Blanco", "Conciencia", "Espiritualidad y conexion."),
]

ZODIAC = [
    "Aries", "Tauro", "Geminis", "Cancer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]

MINERALS = [
    {
        "name": "Quartz",
        "formula": "SiO2",
        "category": "Silicate",
        "crystal_system": "Trigonal",
        "hardness_min": 7,
        "hardness_max": 7,
        "color": "Colorless, white, pink, purple, smoky, and many others",
        "luster": "Vitreous",
        "chakras": ["Corona", "Tercer ojo"],
        "zodiac": ["Leo", "Capricornio"],
        "description": "Common silicate mineral used as a reference species in the starter catalog.",
    },
    {
        "name": "Amethyst",
        "formula": "SiO2",
        "category": "Quartz variety",
        "crystal_system": "Trigonal",
        "hardness_min": 7,
        "hardness_max": 7,
        "color": "Purple",
        "luster": "Vitreous",
        "chakras": ["Tercer ojo", "Corona"],
        "zodiac": ["Piscis", "Acuario"],
        "description": "Purple variety of quartz. Esoteric associations are included as editable starter metadata.",
    },
    {
        "name": "Fluorite",
        "formula": "CaF2",
        "category": "Halide",
        "crystal_system": "Isometric",
        "hardness_min": 4,
        "hardness_max": 4,
        "color": "Variable: green, purple, blue, yellow, colorless",
        "luster": "Vitreous",
        "chakras": ["Tercer ojo", "Corazon"],
        "zodiac": ["Capricornio", "Piscis"],
        "description": "Starter reference record for fluorite.",
    },
    {
        "name": "Citrine",
        "formula": "SiO2",
        "category": "Quartz variety",
        "crystal_system": "Trigonal",
        "hardness_min": 7,
        "hardness_max": 7,
        "color": "Yellow to orange",
        "luster": "Vitreous",
        "chakras": ["Plexo solar"],
        "zodiac": ["Aries", "Leo", "Sagitario"],
        "description": "Yellow to orange quartz variety. Editable starter metadata.",
    },
    {
        "name": "Rose Quartz",
        "formula": "SiO2",
        "category": "Quartz variety",
        "crystal_system": "Trigonal",
        "hardness_min": 7,
        "hardness_max": 7,
        "color": "Pink",
        "luster": "Vitreous",
        "chakras": ["Corazon"],
        "zodiac": ["Tauro", "Libra"],
        "description": "Pink quartz variety. Editable starter metadata.",
    },
]


def get_or_create(db: Session, model, defaults=None, **kwargs):
    item = db.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if item:
        return item
    item = model(**kwargs, **(defaults or {}))
    db.add(item)
    db.flush()
    return item


def seed_all(db: Session) -> None:
    chakra_map = {}
    for name, color, element, notes in CHAKRAS:
        chakra_map[name] = get_or_create(
            db, Chakra, name=name, defaults={"color": color, "element": element, "notes": notes}
        )

    zodiac_map = {}
    for name in ZODIAC:
        zodiac_map[name] = get_or_create(db, ZodiacSign, name=name)

    for row in MINERALS:
        mineral = get_or_create(
            db,
            MineralSpecies,
            name=row["name"],
            defaults={
                "formula": row.get("formula"),
                "category": row.get("category"),
                "crystal_system": row.get("crystal_system"),
                "hardness_min": row.get("hardness_min"),
                "hardness_max": row.get("hardness_max"),
                "color": row.get("color"),
                "luster": row.get("luster"),
                "description": row.get("description"),
            },
        )
        mineral.chakras = [chakra_map[n] for n in row.get("chakras", []) if n in chakra_map]
        mineral.zodiac_signs = [zodiac_map[n] for n in row.get("zodiac", []) if n in zodiac_map]

    if not db.execute(select(CollectionItem)).first():
        quartz = db.execute(select(MineralSpecies).where(MineralSpecies.name == "Quartz")).scalar_one()
        locality = get_or_create(
            db,
            Locality,
            name="Starter locality",
            defaults={"country": "Spain", "region": "Example region", "notes": "Edit or delete this row."},
        )
        db.add(
            CollectionItem(
                item_code="MIN-0001",
                display_name="Starter quartz specimen",
                mineral=quartz,
                locality=locality,
                sold=False,
                special_features="Demo item. Replace with your own specimen.",
                secondary_minerals="",
                purchase_link="",
                notes="This row is created by scripts/init_db.py",
            )
        )

    db.commit()
