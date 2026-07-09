import streamlit as st
from sqlalchemy import func, select

from src.auth import require_admin_access
from src.db import get_session
from src.localities import locality_coordinate_guess, locality_label, normalize_existing_localities
from src.models import CollectionItem, Locality, MineralSpecies, Chakra, ZodiacSign
from src.seeds import seed_all
from src.ui import render_metric_cards, render_page_header, render_section_heading

require_admin_access()

render_page_header(
    "Administracion",
    "Datos de referencia",
    "Gestiona minerales, asociaciones y datos base usados por la coleccion.",
    meta=["Minerales", "Chakras", "Zodiaco"],
)

db = get_session()
try:
    if st.button("Cargar/recargar seed inicial"):
        seed_all(db)
        st.success("Seed cargado.")

    render_section_heading(
        "Localizaciones",
        "Tabla normalizada de origenes reutilizables por varias piezas.",
    )
    locality_rows = (
        db.execute(
            select(Locality, func.count(CollectionItem.id))
            .outerjoin(CollectionItem, CollectionItem.locality_id == Locality.id)
            .group_by(Locality.id)
            .order_by(Locality.country, Locality.region, Locality.mine, Locality.name, Locality.id)
        )
        .all()
    )
    total_items_with_locality = sum(count for _, count in locality_rows)
    mapped_localities = sum(1 for locality, _ in locality_rows if locality_coordinate_guess(locality))
    render_metric_cards(
        [
            ("Localizaciones", len(locality_rows), "Origenes unicos"),
            ("Piezas ubicadas", total_items_with_locality, "Con localidad asignada"),
            ("Mapeables", mapped_localities, "Exactas o aproximadas"),
        ]
    )
    if st.button("Normalizar localizaciones duplicadas", use_container_width=True):
        result = normalize_existing_localities(db)
        db.commit()
        st.success(
            "Localizaciones normalizadas: "
            f"{result['updated']} actualizadas, {result['merged']} duplicadas fusionadas, "
            f"{result['reassigned_items']} piezas reasignadas."
        )
        st.rerun()

    if locality_rows:
        table_rows = []
        for locality, item_count in locality_rows:
            coordinate = locality_coordinate_guess(locality)
            if coordinate:
                coordinates = f"{coordinate.latitude:.5f}, {coordinate.longitude:.5f}"
                map_status = coordinate.note
            else:
                coordinates = ""
                map_status = "Sin coordenada mapeable"
            table_rows.append(
                {
                    "ID": locality.id,
                    "Origen": locality_label(locality),
                    "Pais": locality.country or "",
                    "Region": locality.region or "",
                    "Mina": locality.mine or "",
                    "Localidad": locality.name or "",
                    "Coordenadas": coordinates,
                    "Mapa": map_status,
                    "Piezas": item_count,
                }
            )
        st.dataframe(table_rows, hide_index=True, use_container_width=True)
    else:
        st.info("Todavia no hay localizaciones guardadas.")

    render_section_heading(
        "Crear mineral de referencia",
        "Completa una ficha manual cuando no venga de Mindat.",
    )
    with st.form("mineral"):
        name = st.text_input("Nombre mineral")
        formula = st.text_input("Formula")
        category = st.text_input("Categoria")
        crystal_system = st.text_input("Sistema cristalino")
        hardness_min = st.number_input("Dureza min", min_value=0.0, max_value=10.0, step=0.5)
        hardness_max = st.number_input("Dureza max", min_value=0.0, max_value=10.0, step=0.5)
        color = st.text_input("Color")
        luster = st.text_input("Brillo")
        description = st.text_area("Descripcion")
        chakras = db.execute(select(Chakra).order_by(Chakra.id)).scalars().all()
        zodiac = db.execute(select(ZodiacSign).order_by(ZodiacSign.id)).scalars().all()
        chakra_names = st.multiselect("Chakras", [c.name for c in chakras])
        zodiac_names = st.multiselect("Signos zodiaco", [z.name for z in zodiac])
        save = st.form_submit_button("Guardar mineral")

    if save:
        if not name:
            st.error("Nombre obligatorio.")
            st.stop()

        existing = db.execute(select(MineralSpecies).where(MineralSpecies.name == name)).scalar_one_or_none()
        if existing:
            st.error("Ya existe ese mineral.")
            st.stop()

        mineral = MineralSpecies(
            name=name,
            formula=formula or None,
            category=category or None,
            crystal_system=crystal_system or None,
            hardness_min=hardness_min or None,
            hardness_max=hardness_max or None,
            color=color or None,
            luster=luster or None,
            description=description or None,
        )
        mineral.chakras = [c for c in chakras if c.name in chakra_names]
        mineral.zodiac_signs = [z for z in zodiac if z.name in zodiac_names]
        db.add(mineral)
        db.commit()
        st.success("Mineral guardado.")
finally:
    db.close()
