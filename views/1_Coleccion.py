from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.auth import admin_unlocked
from src.crud import list_collection_items, option_lists
from src.db import UPLOAD_DIR, get_session
from src.item_types import (
    ITEM_TYPE_FILTER_ALL,
    item_type_filter_label,
    item_type_from_filter,
    item_type_label,
    normalize_item_type,
)
from src.item_images import ordered_images
from src.ui import (
    render_collection_card,
    render_metric_cards,
    render_page_header,
    render_section_heading,
)


def cover_image_path(item) -> Path | None:
    for image in ordered_images(item):
        path = UPLOAD_DIR.parent / image.file_path
        if path.exists():
            return path
    return None


def item_label(item) -> str:
    return item.display_name or item.mineral.name


def parse_locality_ids(value: object) -> list[int]:
    if not value:
        return []

    raw_value = value[0] if isinstance(value, list) else value
    locality_ids = []
    for chunk in str(raw_value).split(","):
        try:
            locality_ids.append(int(chunk.strip()))
        except ValueError:
            continue
    return [locality_id for locality_id in locality_ids if locality_id > 0]


def render_gallery(items) -> None:
    item_covers = [(item, cover_image_path(item)) for item in items]

    for row_start in range(0, len(item_covers), 4):
        cols = st.columns(4)
        for offset, (item, cover_path) in enumerate(item_covers[row_start : row_start + 4]):
            with cols[offset]:
                render_collection_card(
                    item_code=item.item_code,
                    item_type=item.item_type,
                    title=item_label(item),
                    mineral_name=item.mineral.name,
                    country=item.locality.country if item.locality else None,
                    sold=bool(item.sold),
                    cover_path=cover_path,
                )
                if st.button(
                    "Ver ficha",
                    key=f"open_item_{item.id}",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state["selected_item_code"] = item.item_code
                    st.query_params.clear()
                    st.switch_page("views/2_Ficha.py")


render_page_header(
    "Galería",
    "Colección completa",
    "Explora las piezas por mineral, procedencia, estado o afinidad. La foto manda; los datos acompañan.",
    meta=["Piezas únicas", "Ficha detallada", "Filtros rápidos"],
)
db = get_session()

try:
    opts = option_lists(db)
    map_locality_ids = parse_locality_ids(st.query_params.get("localidades"))
    map_zone_label = st.query_params.get("zona", "")
    requested_country = st.query_params.get("pais", "")
    requested_item_type = st.query_params.get("tipo", "")
    default_item_type_filter = ITEM_TYPE_FILTER_ALL
    if requested_item_type:
        default_item_type_filter = item_type_filter_label(normalize_item_type(requested_item_type))

    render_section_heading(
        "Filtros",
        "Busca por ID, nombre, mineral o características y afina por tipo, estado o procedencia.",
    )
    with st.container(border=True):
        search_col, type_col, sold_col = st.columns([2, 1, 1])
        text = search_col.text_input("Buscar texto o ID", placeholder="Ej: 1, MIN-0001 o cuarzo")
        type_filter = type_col.selectbox(
            "Tipo",
            opts["item_types"],
            index=opts["item_types"].index(default_item_type_filter),
        )
        sold_filter = sold_col.selectbox("Estado", ["Todos", "Disponible", "Vendido"])

        mineral_col, country_col, chakra_col = st.columns(3)
        mineral = mineral_col.selectbox("Mineral", opts["minerals"])
        default_country_index = (
            opts["countries"].index(requested_country)
            if requested_country in opts["countries"]
            else 0
        )
        country = country_col.selectbox(
            "Ubicación / país",
            opts["countries"],
            index=default_country_index,
        )
        chakra = chakra_col.selectbox("Chakra", opts["chakras"])

    sold = None
    if sold_filter == "Disponible":
        sold = False
    elif sold_filter == "Vendido":
        sold = True
    selected_item_type = item_type_from_filter(type_filter)

    if map_locality_ids or requested_country:
        zone_name = map_zone_label or "zona seleccionada"
        st.info(f"Filtro de mapa activo: {zone_name}.")
        if st.button("Quitar filtro del mapa", use_container_width=False):
            st.query_params.clear()
            st.rerun()

    items = list_collection_items(
        db,
        text=text,
        sold=sold,
        item_type=selected_item_type,
        mineral_name=mineral,
        country=country,
        chakra=chakra,
        locality_ids=map_locality_ids,
    )

    available_count = sum(1 for item in items if not item.sold)
    sold_count = len(items) - available_count
    mineral_count = sum(1 for item in items if normalize_item_type(item.item_type) == "mineral")
    pendant_count = len(items) - mineral_count
    render_metric_cards(
        [
            ("Resultados", len(items), "Piezas encontradas"),
            ("Minerales", mineral_count, item_type_label("mineral", plural=True)),
            ("Colgantes", pendant_count, item_type_label("pendant", plural=True)),
            ("Estado", f"{available_count}/{sold_count}", "Disponibles / vendidas"),
        ]
    )

    if items:
        render_section_heading(
            "Piezas",
            "Abre cualquier ficha para ver fotografías, origen, notas y wiki del mineral.",
            aside=f"{len(items)} resultado(s)",
        )
        render_gallery(items)
    else:
        st.info("No hay piezas que coincidan con los filtros.")

    if admin_unlocked() and items:
        st.divider()
        render_section_heading(
            "Edicion rapida",
            "Abre una pieza filtrada directamente en el formulario de administracion.",
        )
        edit_code = st.selectbox(
            "Pieza",
            [item.item_code for item in items],
            format_func=lambda code: next(
                f"{item.item_code} - {item_label(item)}"
                for item in items
                if item.item_code == code
            ),
        )
        if st.button("Editar pieza seleccionada"):
            st.session_state["editing_item_code"] = edit_code
            st.switch_page("views/3_Alta_edicion.py")
finally:
    db.close()
