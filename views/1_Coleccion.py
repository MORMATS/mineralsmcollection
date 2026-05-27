from __future__ import annotations

from pathlib import Path
import html
from urllib.parse import quote

import streamlit as st

from src.auth import admin_unlocked
from src.db import get_session, UPLOAD_DIR
from src.crud import list_collection_items, option_lists
from src.item_images import ordered_images


def cover_image_path(item) -> Path | None:
    for image in ordered_images(item):
        path = UPLOAD_DIR.parent / image.file_path
        if path.exists():
            return path
    return None


def item_label(item) -> str:
    return item.display_name or item.mineral.name


def render_placeholder(item) -> None:
    initial = (item.mineral.name or "?")[:1].upper()
    st.markdown(
        f"""
        <div class="native-photo-placeholder">
            <span>{initial}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_gallery(items) -> None:
    for row_start in range(0, len(items), 4):
        cols = st.columns(4)
        for offset, item in enumerate(items[row_start : row_start + 4]):
            with cols[offset]:
                cover_path = cover_image_path(item)
                if cover_path:
                    st.image(str(cover_path), width="stretch")
                else:
                    render_placeholder(item)

                st.markdown(
                    (
                        f'<a class="gallery-open-link" href="/Ficha?pieza={quote(item.item_code)}" '
                        f'target="_self">{html.escape(item_label(item))}</a>'
                    ),
                    unsafe_allow_html=True,
                )

                st.caption(f"{item.item_code} · {item.mineral.name}")


st.title("Coleccion completa")
db = get_session()

try:
    opts = option_lists(db)

    with st.sidebar:
        st.header("Filtros")
        text = st.text_input("Buscar texto o ID", placeholder="Ej: 1, MIN-0001 o cuarzo")
        sold_filter = st.selectbox("Estado venta", ["Todos", "Disponible", "Vendido"])
        mineral = st.selectbox("Mineral", opts["minerals"])
        country = st.selectbox("Ubicacion / pais", opts["countries"])
        chakra = st.selectbox("Chakra", opts["chakras"])

    sold = None
    if sold_filter == "Disponible":
        sold = False
    elif sold_filter == "Vendido":
        sold = True

    items = list_collection_items(
        db,
        text=text,
        sold=sold,
        mineral_name=mineral,
        country=country,
        chakra=chakra,
    )

    st.caption(f"{len(items)} pieza(s) encontradas")
    if items:
        render_gallery(items)
    else:
        st.info("No hay piezas que coincidan con los filtros.")

    if admin_unlocked() and items:
        st.divider()
        st.subheader("Edicion rapida")
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
