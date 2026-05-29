from pathlib import Path
import logging

import streamlit as st
from sqlalchemy import or_, select

from src.auth import admin_unlocked
from src.db import UPLOAD_DIR, get_session
from src.item_images import ordered_images
from src.mindat_api import MindatConfigError, upsert_mindat_mineral
from src.models import MineralSpecies
from src.settings import is_production
from src.ui import (
    render_collection_card,
    render_metric_cards,
    render_page_header,
    render_section_heading,
)
from src.wiki_view import render_mineral_wiki


logger = logging.getLogger(__name__)


def item_label(item) -> str:
    return item.display_name or item.mineral.name


def cover_image_path(item) -> Path | None:
    for image in ordered_images(item):
        path = UPLOAD_DIR.parent / image.file_path
        if path.exists():
            return path
    return None


render_page_header(
    "Wiki mineral",
    "Minerales",
    "Consulta propiedades, descripción y piezas de la colección asociadas a cada especie mineral.",
    meta=["Referencia", "Mindat", "Piezas relacionadas"],
)

db = get_session()
try:
    render_section_heading(
        "Buscar mineral",
        "Filtra por nombre, fórmula, color, categoría o descripción.",
    )
    with st.container(border=True):
        query = st.text_input("Buscar mineral", placeholder="Nombre, fórmula, color, descripción...")

    stmt = select(MineralSpecies).order_by(MineralSpecies.name)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                MineralSpecies.name.ilike(like),
                MineralSpecies.formula.ilike(like),
                MineralSpecies.color.ilike(like),
                MineralSpecies.description.ilike(like),
                MineralSpecies.category.ilike(like),
            )
        )

    minerals = db.execute(stmt).scalars().all()
    if not minerals:
        st.info("No hay minerales que coincidan con la búsqueda.")
        st.stop()

    mineral_names = [mineral.name for mineral in minerals]
    default_name = st.session_state.get("selected_mineral_name")
    default_index = mineral_names.index(default_name) if default_name in mineral_names else 0
    selected_name = st.selectbox("Mineral", mineral_names, index=default_index)
    mineral = next(item for item in minerals if item.name == selected_name)
    st.session_state["selected_mineral_name"] = selected_name

    render_metric_cards(
        [
            ("Piezas", len(mineral.items), "En la colección"),
            ("Mindat ID", mineral.mindat_id or "-", "Referencia externa"),
            ("Datos API", "Sí" if mineral.api_raw_json else "No", "Enriquecimiento"),
        ]
    )

    if admin_unlocked() and st.button("Actualizar este mineral desde Mindat", use_container_width=True):
        try:
            updated, message = upsert_mindat_mineral(db, mineral.name)
        except MindatConfigError as exc:
            st.error(str(exc))
        except Exception as exc:
            logger.exception("Error updating Mindat mineral %s", mineral.name)
            if is_production():
                st.error("Error consultando Mindat. Revisa los logs del servicio.")
            else:
                st.error(f"Error consultando Mindat: {exc}")
        else:
            if updated:
                st.success(message)
                st.rerun()
            else:
                st.warning(message)

    render_mineral_wiki(mineral)

    if mineral.items:
        related_items = sorted(mineral.items, key=lambda item: item.created_at, reverse=True)
        render_section_heading(
            "Piezas de tu colección",
            "Ejemplares vinculados a este mineral.",
            aside=f"{len(related_items)} pieza(s)",
        )
        for row_start in range(0, len(related_items), 4):
            cols = st.columns(4)
            for offset, item in enumerate(related_items[row_start : row_start + 4]):
                with cols[offset]:
                    render_collection_card(
                        item_code=item.item_code,
                        title=item_label(item),
                        mineral_name=mineral.name,
                        country=item.locality.country if item.locality else None,
                        sold=bool(item.sold),
                        cover_path=cover_image_path(item),
                    )
                    if st.button(
                        "Ver ficha",
                        key=f"wiki_item_{item.id}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_item_code"] = item.item_code
                        st.switch_page("views/2_Ficha.py")

finally:
    db.close()
