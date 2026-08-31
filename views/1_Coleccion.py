from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.auth import admin_unlocked
from src.collection_export import build_collection_workbook
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
DEFAULT_GALLERY_PAGE_SIZE = "Todos"
LABEL_SELECTION_KEY = "collection_label_selection"
LABEL_PANEL_KEY = "collection_labels_open"
EXCEL_SELECTION_KEY = "collection_excel_selection"
EXCEL_PANEL_KEY = "collection_excel_open"
FILTER_WIDGET_KEYS = (
    "collection_search",
    "collection_type",
    "collection_status",
    "collection_mineral",
    "collection_country",
    "collection_chakra",
    "collection_sort",
    "collection_page_number",
    "collection_page_size",
)


def cover_image_path(item) -> Path | None:
    for image in ordered_images(item):
        path = UPLOAD_DIR.parent / image.file_path
        if path.exists():
            return path
    return None


def item_label(item) -> str:
    return item.display_name or item.mineral.name


def reset_collection_view() -> None:
    for key in FILTER_WIDGET_KEYS:
        st.session_state.pop(key, None)
    clear_collection_filters()
    st.query_params.clear()


def sort_collection_items(items: list, sort_mode: str) -> list:
    if sort_mode == "Nombre A–Z":
        return sorted(items, key=lambda item: (item_label(item).casefold(), item.item_code))
    if sort_mode == "ID ascendente":
        return sorted(items, key=lambda item: item.item_code)
    if sort_mode == "Disponibles primero":
        return sorted(items, key=lambda item: (bool(item.sold), item_label(item).casefold()))
    return items


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
    if len(items) <= min(option for option in GALLERY_PAGE_SIZE_OPTIONS if isinstance(option, int)):
        return items, 1, 1, len(items)

    control_col, page_col = st.columns([1, 1])
    page_size = control_col.selectbox(
        "Piezas por página",
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
        "Página",
        min_value=1,
        max_value=total_pages,
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
            "Piezas para imprimir",
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


def render_excel_panel(items: list) -> None:
    item_by_code = {item.item_code: item for item in items}
    valid_codes = list(item_by_code)
    current_selection = [
        code
        for code in st.session_state.get(EXCEL_SELECTION_KEY, [])
        if code in item_by_code
    ]
    st.session_state[EXCEL_SELECTION_KEY] = current_selection

    with st.container(border=True):
        title_col, close_col = st.columns([5, 1])
        with title_col:
            render_section_heading(
                "Exportar a Excel",
                "Selecciona las piezas que quieres incluir. La lista respeta los filtros actuales.",
                aside="Excel · .xlsx",
            )
        if close_col.button("Cerrar", key="close_collection_excel", use_container_width=True):
            st.session_state[EXCEL_PANEL_KEY] = False
            st.rerun()

        action_col, clear_col = st.columns(2)
        if action_col.button(
            "Seleccionar todas",
            key="select_all_collection_excel",
            use_container_width=True,
        ):
            st.session_state[EXCEL_SELECTION_KEY] = valid_codes
            st.rerun()
        if clear_col.button(
            "Limpiar selección",
            key="clear_collection_excel",
            use_container_width=True,
        ):
            st.session_state[EXCEL_SELECTION_KEY] = []
            st.rerun()

        selected_codes = st.multiselect(
            "Piezas para exportar",
            valid_codes,
            key=EXCEL_SELECTION_KEY,
            format_func=lambda code: f"{code} · {item_label(item_by_code[code])}",
            placeholder="Selecciona una o varias piezas",
        )

        if not selected_codes:
            st.info("Selecciona al menos una pieza para preparar el archivo Excel.")
            return

        selected_code_set = set(selected_codes)
        selected_items = [item for item in items if item.item_code in selected_code_set]
        st.caption(
            f"El archivo incluirá {len(selected_items)} pieza(s), con datos de inventario, "
            "material principal y procedencia."
        )
        workbook_data = build_collection_workbook(selected_items)
        st.download_button(
            "Descargar Excel",
            data=workbook_data,
            file_name=f"coleccion-minerales-{len(selected_items)}-piezas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
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
        text = search_col.text_input(
            "Buscar texto o ID",
            placeholder="Ej.: 1, MIN-0001 o cuarzo",
            key="collection_search",
        )
        type_filter = type_col.selectbox(
            "Tipo",
            opts["item_types"],
            index=opts["item_types"].index(default_item_type_filter),
            key="collection_type",
        )
        sold_filter = sold_col.selectbox(
            "Estado",
            ["Todos", "Disponible", "Vendido"],
            key="collection_status",
        )

        mineral_col, country_col, chakra_col, sort_col = st.columns(4)
        mineral = mineral_col.selectbox("Mineral", opts["minerals"], key="collection_mineral")
        default_country_index = (
            opts["countries"].index(requested_country)
            if requested_country in opts["countries"]
            else 0
        )
        country = country_col.selectbox(
            "Ubicación / país",
            opts["countries"],
            index=default_country_index,
            key="collection_country",
        )
        chakra = chakra_col.selectbox("Chakra", opts["chakras"], key="collection_chakra")
        sort_mode = sort_col.selectbox(
            "Ordenar",
            ["Más recientes", "Nombre A–Z", "ID ascendente", "Disponibles primero"],
            key="collection_sort",
        )

        active_filter_count = sum(
            (
                bool(text.strip()),
                type_filter != ITEM_TYPE_FILTER_ALL,
                sold_filter != "Todos",
                mineral != "Todos",
                country != "Todos",
                chakra != "Todos",
                bool(map_locality_ids),
            )
        )
        reset_col, filter_summary_col = st.columns([1, 3])
        reset_col.button(
            "Limpiar filtros",
            icon=":material/filter_alt_off:",
            key="collection_reset_filters",
            disabled=active_filter_count == 0 and sort_mode == "Más recientes",
            on_click=reset_collection_view,
            use_container_width=True,
        )
        filter_summary_col.caption(
            "Vista sin filtros" if active_filter_count == 0 else f"{active_filter_count} filtro(s) activo(s)"
        )

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
    items = sort_collection_items(items, sort_mode)

    available_count = sum(1 for item in items if not item.sold)
    sold_count = len(items) - available_count
    mineral_count = sum(1 for item in items if normalize_item_type(item.item_type) == "mineral")
    pendant_count = sum(1 for item in items if normalize_item_type(item.item_type) == "pendant")
    fossil_count = sum(1 for item in items if normalize_item_type(item.item_type) == "fossil")
    render_metric_cards(
        [
            ("Resultados", len(items), "Piezas encontradas"),
            ("Minerales", mineral_count, item_type_label("mineral", plural=True)),
            ("Colgantes", pendant_count, item_type_label("pendant", plural=True)),
            ("Fósiles", fossil_count, item_type_label("fossil", plural=True)),
            ("Estado", f"{available_count}/{sold_count}", "Disponibles / vendidas"),
        ]
    )

    if items:
        labels_col, excel_col, _ = st.columns([1.5, 1.5, 2])
        if labels_col.button(
            "Imprimir etiquetas",
            icon=":material/label:",
            use_container_width=True,
            help="Seleccionar minerales y preparar etiquetas para imprimir.",
        ):
            st.session_state[LABEL_PANEL_KEY] = True
        if excel_col.button(
            "Exportar Excel",
            icon=":material/table_view:",
            use_container_width=True,
            help="Seleccionar piezas y descargar sus datos en un archivo Excel.",
        ):
            st.session_state[EXCEL_PANEL_KEY] = True
        if st.session_state.get(LABEL_PANEL_KEY, False):
            render_labels_panel(items)
        if st.session_state.get(EXCEL_PANEL_KEY, False):
            render_excel_panel(items)

        visible_items, current_page, total_pages, page_size = paginated_items(items)
        if total_pages > 1:
            st.caption(f"Mostrando {len(visible_items)} de {len(items)} piezas · página {current_page}/{total_pages}.")

        render_section_heading(
            "Piezas",
            "Abre cualquier ficha para ver fotografías, origen, notas y datos de referencia.",
            aside=f"{len(items)} resultado(s)",
        )
        render_gallery(visible_items)
    else:
        st.info("No hay piezas que coincidan con los filtros actuales.")
        st.button(
            "Restablecer búsqueda",
            icon=":material/refresh:",
            on_click=reset_collection_view,
            use_container_width=False,
        )

    if admin_unlocked() and items:
        st.divider()
        render_section_heading(
            "Edición rápida",
            "Abre una pieza filtrada directamente en el formulario de administración.",
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
