import logging
from pathlib import Path

import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from src.auth import admin_unlocked, render_admin_sidebar
from src.db import get_session, UPLOAD_DIR
from src.errors import is_schema_migration_error
from src.item_types import ITEM_TYPE_MINERAL, ITEM_TYPE_PENDANT
from src.item_images import ordered_images
from src.models import CollectionItem, MineralSpecies
from src.settings import is_production
from src.ui import (
    render_collection_card,
    render_global_styles,
    render_metric_cards,
    render_page_header,
    render_section_heading,
)


st.set_page_config(page_title="Minerales", page_icon=":gem:", layout="wide")
render_global_styles()
logger = logging.getLogger(__name__)


def cover_image_path(item: CollectionItem) -> Path | None:
    for image in ordered_images(item):
        path = UPLOAD_DIR.parent / image.file_path
        if path.exists():
            return path
    return None


def item_label(item: CollectionItem) -> str:
    return item.display_name or item.mineral.name


def home_page() -> None:
    render_page_header(
        "Colección privada",
        "Minerales",
        "Catálogo visual de piezas seleccionadas, con ficha propia y referencia mineral para descubrir cada ejemplar con calma.",
        meta=["Ismael Guessous", "Galería pública", "Wiki mineral"],
    )

    db = get_session()
    try:
        total_items = db.scalar(select(func.count(CollectionItem.id))) or 0
        total_minerals = db.scalar(select(func.count(MineralSpecies.id))) or 0
        sold_items = db.scalar(select(func.count(CollectionItem.id)).where(CollectionItem.sold == True)) or 0
        available_items = max(total_items - sold_items, 0)
        mineral_items = (
            db.scalar(
                select(func.count(CollectionItem.id)).where(CollectionItem.item_type == ITEM_TYPE_MINERAL)
            )
            or 0
        )
        pendant_items = (
            db.scalar(
                select(func.count(CollectionItem.id)).where(CollectionItem.item_type == ITEM_TYPE_PENDANT)
            )
            or 0
        )

        render_metric_cards(
            [
                ("Piezas", total_items, f"{available_items} disponibles"),
                ("Minerales", mineral_items, f"{total_minerals} fichas de referencia"),
                ("Colgantes", pendant_items, "Piezas tipo joya"),
                ("Vendidas", sold_items, "Histórico de la colección"),
            ]
        )

        render_section_heading(
            "Búsqueda rápida",
            "Abre una ficha por ID si ya sabes qué pieza quieres consultar.",
        )
        search_col, action_col = st.columns([3, 1])
        item_code = search_col.text_input(
            "ID / código de pieza",
            placeholder="Ej: 12 o MIN-0012",
            label_visibility="collapsed",
        )
        if action_col.button("Abrir ficha", type="primary", use_container_width=True) and item_code:
            st.session_state["selected_item_code"] = item_code.strip()
            st.switch_page("views/2_Ficha.py")

        latest_items = (
            db.execute(
                select(CollectionItem)
                .options(
                    joinedload(CollectionItem.mineral),
                    joinedload(CollectionItem.locality),
                    joinedload(CollectionItem.images),
                )
                .order_by(CollectionItem.created_at.desc())
                .limit(4)
            )
            .unique()
            .scalars()
            .all()
        )

        if latest_items:
            render_section_heading(
                "Últimas piezas",
                "Una entrada directa a los ejemplares añadidos recientemente.",
                aside=f"{len(latest_items)} destacadas",
            )
            cols = st.columns(4)
            for col, item in zip(cols, latest_items):
                with col:
                    render_collection_card(
                        item_code=item.item_code,
                        item_type=item.item_type,
                        title=item_label(item),
                        mineral_name=item.mineral.name,
                        country=item.locality.country if item.locality else None,
                        sold=bool(item.sold),
                        cover_path=cover_image_path(item),
                    )
                    if st.button(
                        "Ver ficha",
                        key=f"home_open_item_{item.id}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_item_code"] = item.item_code
                        st.switch_page("views/2_Ficha.py")
    finally:
        db.close()


public_pages = [
    st.Page(home_page, title="Inicio", icon=":material/home:", default=True),
    st.Page("views/1_Coleccion.py", title="Colección", icon=":material/grid_view:"),
    st.Page("views/7_Mapa.py", title="Mapa", icon=":material/travel_explore:"),
    st.Page("views/2_Ficha.py", title="Ficha", icon=":material/search:"),
    st.Page("views/6_Wiki_minerales.py", title="Wiki minerales", icon=":material/menu_book:"),
]

admin_pages = [
    st.Page("views/3_Alta_edicion.py", title="Alta/edición", icon=":material/add_circle:"),
    st.Page("views/4_Admin_datos.py", title="Admin datos", icon=":material/database:"),
    st.Page("views/5_Importar_API.py", title="Importar API", icon=":material/cloud_download:"),
]

pages = {"Catálogo": public_pages}
if admin_unlocked():
    pages["Administración"] = admin_pages


def handle_map_link_navigation() -> None:
    map_item = st.query_params.get("map_item")
    map_country = st.query_params.get("map_pais")
    map_localities = st.query_params.get("map_localidades")
    map_zone = st.query_params.get("map_zona")
    map_type = st.query_params.get("map_tipo")

    if map_item:
        st.session_state["selected_item_code"] = map_item
        st.query_params.clear()
        st.query_params["pieza"] = map_item
        st.switch_page("views/2_Ficha.py")

    if map_country or map_localities:
        st.query_params.clear()
        if map_country:
            st.query_params["pais"] = map_country
        if map_localities:
            st.query_params["localidades"] = map_localities
        if map_zone:
            st.query_params["zona"] = map_zone
        if map_type:
            st.query_params["tipo"] = map_type
        st.switch_page("views/1_Coleccion.py")


handle_map_link_navigation()
selected_page = st.navigation(pages)
render_admin_sidebar()
try:
    selected_page.run()
except Exception as exc:
    logger.exception("Unhandled application error")
    if is_production():
        if is_schema_migration_error(exc):
            st.error("La base de datos necesita una actualizacion. Ejecuta las migraciones y reinicia el servicio.")
        else:
            st.error("No se pudo cargar esta vista. Revisa el servicio o intentalo de nuevo mas tarde.")
    else:
        raise
