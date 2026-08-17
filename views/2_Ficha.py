import json
import logging

import streamlit as st

from src.auth import admin_unlocked
from src.crud import get_item_by_code, normalize_item_code
from src.db import UPLOAD_DIR, get_session
from src.item_types import item_type_label
from src.item_images import ordered_images
from src.mindat_api import MindatConfigError, update_mindat_locality
from src.navigation import switch_to_admin_edit
from src.ui import (
    render_detail_grid,
    render_metric_cards,
    render_page_header,
    render_section_heading,
    render_stable_photo,
    shared_image_frame_ratio,
    status_label,
)
from src.wiki import load_mindat_raw, mineral_elements, mineral_formula
from src.wiki_view import render_generic_photo, render_mineral_wiki


logger = logging.getLogger(__name__)


def move_photo(key: str, count: int, delta: int) -> None:
    current = int(st.session_state.get(key, 0))
    st.session_state[key] = (current + delta) % count


def clean_display(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def visible_rows(rows: list[tuple[str, object]]) -> list[tuple[str, str]]:
    result = []
    for label, value in rows:
        display_value = clean_display(value)
        if display_value:
            result.append((label, display_value))
    return result


def render_visible_section(title: str, rows: list[tuple[str, str]]) -> None:
    st.markdown(f"#### {title}")
    render_detail_grid(rows)


def render_optional_section(title: str, rows: list[tuple[str, object]]) -> bool:
    visible = visible_rows(rows)
    if not visible:
        return False

    render_visible_section(title, visible)
    return True


def render_item_details(item) -> bool:
    sections = []
    if item.locality:
        locality_rows = visible_rows(
            [
                ("Localidad", item.locality.name),
                ("Mina / yacimiento", item.locality.mine),
                ("Región", item.locality.region),
                ("País", item.locality.country),
                ("ID localidad", item.locality_id),
                ("Mindat locality ID", item.locality.mindat_locality_id),
                ("Latitud", item.locality.latitude),
                ("Longitud", item.locality.longitude),
                ("Fuente Mindat", item.locality.source_url),
                ("Actualizada", item.locality.updated_at),
                ("Descripcion", item.locality.notes),
            ]
        )
        if locality_rows:
            sections.append(("Origen", locality_rows))

    index_rows = visible_rows(
        [
            ("Tipo", item_type_label(item.item_type)),
            ("Características especiales", item.special_features),
            ("Minerales secundarios", item.secondary_minerals),
            ("Notas", item.notes),
        ]
    )
    if index_rows:
        sections.append(("Datos de índice", index_rows))

    raw = load_mindat_raw(item.mineral)
    mineral_rows = visible_rows(
        [
            ("Fórmula", mineral_formula(item.mineral, raw)),
            ("Elementos", mineral_elements(item.mineral, raw)),
            ("ID Mindat", item.mineral.mindat_id),
        ]
    )
    if mineral_rows:
        sections.append(("Mineral Mindat", mineral_rows))

    if not sections:
        st.info("Esta pieza todavía no tiene datos descriptivos adicionales.")
        return False

    for title, rows in sections:
        render_visible_section(title, rows)

    if item.locality and item.locality.api_raw_json:
        try:
            raw_locality = json.loads(item.locality.api_raw_json)
        except (TypeError, ValueError):
            raw_locality = item.locality.api_raw_json
        with st.expander("Datos completos de la localidad en Mindat"):
            if isinstance(raw_locality, str):
                st.code(raw_locality, language="json")
            else:
                st.json(raw_locality)
    return True


def existing_item_images(item):
    return [
        image
        for image in ordered_images(item)
        if (UPLOAD_DIR.parent / image.file_path).exists()
    ]


def render_item_photos(item) -> None:
    images = existing_item_images(item)
    image_paths = [UPLOAD_DIR.parent / image.file_path for image in images]
    photo_frame_ratio = shared_image_frame_ratio(image_paths)

    if not images:
        st.info("Esta pieza no tiene fotos locales disponibles.")
        st.caption("Foto genérica del mineral")
        render_generic_photo(item.mineral.name)
        return

    state_key = f"photo_index_{item.item_code}"
    try:
        current = int(st.session_state.get(state_key, 0))
    except (TypeError, ValueError):
        current = 0
    current = max(0, min(current, len(images) - 1))
    st.session_state[state_key] = current

    image = images[current]
    render_stable_photo(
        UPLOAD_DIR.parent / image.file_path,
        photo_frame_ratio,
        caption=image.caption,
    )

    if len(images) == 1:
        st.caption("Foto 1 de 1")
        return

    previous_col, count_col, next_col = st.columns([1, 2, 1])
    previous_col.button(
        "Anterior",
        key=f"{state_key}_previous",
        help="Foto anterior",
        on_click=move_photo,
        args=(state_key, len(images), -1),
        use_container_width=True,
    )
    count_col.markdown(
        f'<div style="text-align:center; color: var(--mineral-muted); padding-top: .55rem;">Foto {current + 1} de {len(images)}</div>',
        unsafe_allow_html=True,
    )
    next_col.button(
        "Siguiente",
        key=f"{state_key}_next",
        help="Foto siguiente",
        on_click=move_photo,
        args=(state_key, len(images), 1),
        use_container_width=True,
    )


def item_location_label(item) -> str:
    if not item.locality:
        return "Origen por completar"
    parts = [item.locality.mine, item.locality.region, item.locality.country]
    return " · ".join(part for part in parts if part) or "Origen por completar"


query_code = st.query_params.get("pieza")
default_code = normalize_item_code(query_code) if query_code else st.session_state.get("selected_item_code", "")

render_page_header(
    "Ficha de pieza",
    "Consulta",
    "Busca una pieza por ID para ver sus fotografías, datos de origen y ficha mineral asociada.",
    meta=["Galería", "Datos de pieza", "Wiki mineral"],
)

with st.container(border=True):
    with st.form("item_lookup"):
        search_col, button_col = st.columns([3, 1])
        typed_code = search_col.text_input(
            "ID de pieza",
            value=default_code,
            placeholder="Ej: 1 o MIN-0001",
        )
        lookup_submitted = button_col.form_submit_button(
            "Buscar",
            type="primary",
            use_container_width=True,
        )

if lookup_submitted and typed_code:
    st.session_state["selected_item_code"] = normalize_item_code(typed_code)
    st.rerun()

item_code = normalize_item_code(query_code or st.session_state.get("selected_item_code", typed_code))

db = get_session()
try:
    if item_code:
        item = get_item_by_code(db, item_code.strip())
        if not item:
            st.warning("No existe una pieza con ese ID.")
            st.stop()

        images = existing_item_images(item)
        render_section_heading(
            item.display_name or item.mineral.name,
            item_location_label(item),
            aside=item.item_code,
        )
        render_metric_cards(
            [
                ("Mineral", item.mineral.name, "Principal"),
                ("Tipo", item_type_label(item.item_type), "Clasificación"),
                ("Estado", status_label(bool(item.sold)), "Disponibilidad"),
                ("Fotos", len(images), "Locales disponibles"),
            ]
        )

        action_cols = st.columns([1.3, 1.1, 1.7, 1.9])
        if item.purchase_link:
            action_cols[0].link_button("Comprar / ver anuncio", item.purchase_link, use_container_width=True)
        if admin_unlocked() and action_cols[1].button("Editar pieza", use_container_width=True):
            switch_to_admin_edit(item.item_code)
        if admin_unlocked():
            can_update_locality = bool(item.locality and item.locality.mindat_locality_id)
            if action_cols[2].button(
                "Actualizar localización",
                disabled=not can_update_locality,
                help=(
                    "Consulta Mindat y actualiza todas las piezas vinculadas a esta localidad."
                    if can_update_locality
                    else "Asigna primero el ID de localidad Mindat desde Editar pieza."
                ),
                use_container_width=True,
            ):
                try:
                    with st.spinner("Consultando la localidad en Mindat..."):
                        _, message = update_mindat_locality(db, item.locality)
                    st.success(message)
                except MindatConfigError as exc:
                    st.error(str(exc))
                except LookupError as exc:
                    st.warning(str(exc))
                except Exception:
                    logger.exception("Error updating Mindat locality for item %s", item.item_code)
                    st.error("No se pudo actualizar la localidad. Revisa los logs del servicio.")

        pieza_tab, wiki_tab = st.tabs(["Pieza", "Wiki mineral"])

        with pieza_tab:
            left, right = st.columns([1.05, 1.55])
            with left:
                render_item_photos(item)

            with right:
                render_item_details(item)

        with wiki_tab:
            chakra_names = ", ".join(c.name for c in item.mineral.chakras)
            zodiac_names = ", ".join(z.name for z in item.mineral.zodiac_signs)
            render_mineral_wiki(item.mineral)
            render_optional_section(
                "Asociaciones personales",
                [
                    ("Chakras", chakra_names),
                    ("Zodiaco", zodiac_names),
                ],
            )
    else:
        st.info("Introduce un ID para buscar una pieza.")
finally:
    db.close()
