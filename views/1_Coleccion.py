from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.auth import admin_unlocked
from src.db import get_session, UPLOAD_DIR
from src.crud import list_collection_items, option_lists
from src.item_images import ordered_images
from src.ui import render_stable_photo, shared_image_frame_ratio


def cover_image_path(item) -> Path | None:
    for image in ordered_images(item):
        path = UPLOAD_DIR.parent / image.file_path
        if path.exists():
            return path
    return None


def item_label(item) -> str:
    return item.display_name or item.mineral.name


def render_placeholder(item, frame_ratio: float = 1.0) -> None:
    initial = (item.mineral.name or "?")[:1].upper()
    st.markdown(
        f"""
        <div class="native-photo-placeholder" style="--photo-frame-ratio: {frame_ratio:.6f};">
            <span>{initial}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_gallery(items) -> None:
    item_covers = [(item, cover_image_path(item)) for item in items]
    cover_paths = [path for _, path in item_covers if path]
    photo_frame_ratio = shared_image_frame_ratio(cover_paths)

    for row_start in range(0, len(item_covers), 4):
        cols = st.columns(4)
        for offset, (item, cover_path) in enumerate(item_covers[row_start : row_start + 4]):
            with cols[offset]:
                if cover_path:
                    render_stable_photo(cover_path, photo_frame_ratio)
                else:
                    render_placeholder(item, photo_frame_ratio)

                if st.button(
                    item_label(item),
                    key=f"open_item_{item.id}",
                    use_container_width=True,
                ):
                    st.session_state["selected_item_code"] = item.item_code
                    st.query_params.clear()
                    st.switch_page("views/2_Ficha.py")

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
