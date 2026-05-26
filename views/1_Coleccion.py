from __future__ import annotations

import base64
import html
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from PIL import Image, UnidentifiedImageError
import streamlit as st

from src.auth import admin_unlocked
from src.db import get_session, UPLOAD_DIR
from src.crud import list_collection_items, option_lists
from src.item_images import ordered_images


THUMBNAIL_SIZE = (680, 680)


@st.cache_data(show_spinner=False)
def photo_data_uri(path_text: str, mtime: float) -> str:
    path = Path(path_text)
    if not path.exists():
        return ""

    try:
        with Image.open(path) as image:
            image.thumbnail(THUMBNAIL_SIZE)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="WEBP", quality=82, method=6)
    except (OSError, UnidentifiedImageError):
        return ""

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/webp;base64,{encoded}"


def cover_image(item):
    images = ordered_images(item)
    return images[0] if images else None


def cover_uri(item) -> str:
    image = cover_image(item)
    if not image:
        return ""
    path = UPLOAD_DIR.parent / image.file_path
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return ""
    return photo_data_uri(str(path), mtime)


def item_location(item) -> str:
    if not item.locality:
        return ""
    return ", ".join(
        value
        for value in [item.locality.mine, item.locality.region, item.locality.country]
        if value
    )


def render_gallery(items) -> None:
    cards = []
    for item in items:
        title = item.display_name or item.mineral.name
        location = item_location(item)
        badge = "Vendido" if item.sold else item.item_code
        image_uri = cover_uri(item)
        href = f"?pieza={quote(item.item_code)}"
        label = html.escape(f"{item.item_code} - {title}")

        if image_uri:
            media = f'<img src="{image_uri}" alt="{label}" loading="lazy">'
        else:
            media = (
                '<div class="collection-placeholder">'
                f"<span>{html.escape(item.mineral.name[:1].upper())}</span>"
                "</div>"
            )

        cards.append(
            f"""
            <a class="collection-card" href="{href}" target="_self" aria-label="{label}">
                <span class="collection-photo">{media}</span>
                <span class="collection-overlay">
                    <span class="collection-badge">{html.escape(badge)}</span>
                    <span class="collection-title">{html.escape(title)}</span>
                    <span class="collection-meta">{html.escape(item.mineral.name)}</span>
                    <span class="collection-meta">{html.escape(location)}</span>
                </span>
            </a>
            """
        )

    st.markdown('<div class="collection-grid">' + "\n".join(cards) + "</div>", unsafe_allow_html=True)


selected_from_gallery = st.query_params.get("pieza")
if selected_from_gallery:
    st.session_state["selected_item_code"] = selected_from_gallery
    st.query_params.clear()
    st.switch_page("views/2_Ficha.py")


st.title("Coleccion completa")
db = get_session()

try:
    opts = option_lists(db)

    with st.sidebar:
        st.header("Filtros")
        text = st.text_input("Buscar texto o ID", placeholder="Ej: 12, MIN-0012 o cuarzo")
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
                f"{item.item_code} - {item.display_name or item.mineral.name}"
                for item in items
                if item.item_code == code
            ),
        )
        if st.button("Editar pieza seleccionada"):
            st.session_state["editing_item_code"] = edit_code
            st.switch_page("views/3_Alta_edicion.py")
finally:
    db.close()
