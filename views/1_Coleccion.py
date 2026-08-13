from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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
from src.labels import (
    generate_labels_pdf,
    labels_preview_html,
    mineral_label_from_item,
)
from src.navigation import clear_collection_filters, collection_filters, switch_to_admin_edit, switch_to_item
from src.ui import (
    render_collection_card,
    render_metric_cards,
    render_page_header,
    render_section_heading,
)


GALLERY_PAGE_SIZE_OPTIONS = [12, 24, 48, "Todos"]
DEFAULT_GALLERY_PAGE_SIZE = 24
LABEL_SELECTION_KEY = "collection_label_selection"
LABEL_PANEL_KEY = "collection_labels_open"


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
                    switch_to_item(item.item_code)


def paginated_items(items: list) -> tuple[list, int, int, int | str]:
    if len(items) <= DEFAULT_GALLERY_PAGE_SIZE:
        return items, 1, 1, len(items)

    control_col, page_col = st.columns([1, 1])
    page_size = control_col.selectbox(
        "Piezas por pagina",
        GALLERY_PAGE_SIZE_OPTIONS,
        index=GALLERY_PAGE_SIZE_OPTIONS.index(DEFAULT_GALLERY_PAGE_SIZE),
        key="collection_page_size",
    )
    if page_size == "Todos":
        return items, 1, 1, page_size

    total_pages = max((len(items) + int(page_size) - 1) // int(page_size), 1)
    current_default = min(int(st.session_state.get("collection_page_number", 1)), total_pages)
    st.session_state["collection_page_number"] = current_default
    page = page_col.number_input(
        "Pagina",
        min_value=1,
        max_value=total_pages,
        value=current_default,
        step=1,
        key="collection_page_number",
    )
    start = (int(page) - 1) * int(page_size)
    return items[start : start + int(page_size)], int(page), total_pages, page_size


def render_labels_panel(items: list) -> None:
    item_by_code = {item.item_code: item for item in items}
    valid_codes = list(item_by_code)
    current_selection = [
        code
        for code in st.session_state.get(LABEL_SELECTION_KEY, [])
        if code in item_by_code
    ]
    st.session_state[LABEL_SELECTION_KEY] = current_selection

    with st.container(border=True):
        title_col, close_col = st.columns([5, 1])
        with title_col:
            render_section_heading(
                "Etiquetas",
                "Elige las piezas. Cada etiqueta mide exactamente 30 × 15 mm en el PDF.",
                aside="Vista previa ×2",
            )
        if close_col.button("Cerrar", key="close_collection_labels", use_container_width=True):
            st.session_state[LABEL_PANEL_KEY] = False
            st.rerun()

        action_col, clear_col = st.columns(2)
        if action_col.button(
            "Seleccionar todos",
            key="select_all_collection_labels",
            use_container_width=True,
        ):
            st.session_state[LABEL_SELECTION_KEY] = valid_codes
            st.rerun()
        if clear_col.button(
            "Limpiar selección",
            key="clear_collection_labels",
            use_container_width=True,
        ):
            st.session_state[LABEL_SELECTION_KEY] = []
            st.rerun()

        selected_codes = st.multiselect(
            "Minerales para imprimir",
            valid_codes,
            key=LABEL_SELECTION_KEY,
            format_func=lambda code: f"{code} · {item_label(item_by_code[code])}",
            placeholder="Selecciona una o varias piezas",
        )
        selected_labels = [
            mineral_label_from_item(item_by_code[code]) for code in selected_codes
        ]

        if not selected_labels:
            st.info("Selecciona al menos una pieza para ver sus etiquetas.")
            return

        st.caption(
            f"Vista previa de {len(selected_labels)} etiqueta(s). "
            "El PDF las distribuye en hojas A4, listas para imprimir al 100 % de escala."
        )
        components.html(
            labels_preview_html(selected_labels),
            height=500,
            scrolling=False,
        )
        pdf_data = generate_labels_pdf(selected_labels)
        st.download_button(
            "Descargar PDF de etiquetas",
            data=pdf_data,
            file_name="etiquetas-minerales.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )


render_page_header(
    "Galería",
    "Colección completa",
    "Explora las piezas por mineral, procedencia, estado o afinidad. La foto manda; los datos acompañan.",
    meta=["Piezas únicas", "Ficha detallada", "Filtros rápidos"],
)
db = get_session()

try:
    opts = option_lists(db)
    active_map_filters = collection_filters()
    map_locality_ids = parse_locality_ids(active_map_filters.get("localidades"))
    map_zone_label = active_map_filters.get("zona", "")
    requested_country = active_map_filters.get("pais", "")
    requested_item_type = active_map_filters.get("tipo", "")
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
            clear_collection_filters()
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
        labels_col, _ = st.columns([1, 4])
        if labels_col.button(
            "Labels",
            icon=":material/label:",
            use_container_width=True,
            type="primary",
            help="Seleccionar minerales y preparar etiquetas para imprimir.",
        ):
            st.session_state[LABEL_PANEL_KEY] = True
        if st.session_state.get(LABEL_PANEL_KEY, False):
            render_labels_panel(items)

        visible_items, current_page, total_pages, page_size = paginated_items(items)
        if total_pages > 1:
            st.caption(f"Mostrando {len(visible_items)} de {len(items)} piezas - pagina {current_page}/{total_pages}.")

        render_section_heading(
            "Piezas",
            "Abre cualquier ficha para ver fotografías, origen, notas y wiki del mineral.",
            aside=f"{len(items)} resultado(s)",
        )
        render_gallery(visible_items)
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
            switch_to_admin_edit(edit_code)
finally:
    db.close()
