import logging

import streamlit as st
from sqlalchemy import or_, select

from src.auth import admin_unlocked
from src.db import get_session
from src.mindat_api import MindatConfigError, upsert_mindat_mineral
from src.models import MineralSpecies
from src.settings import is_production
from src.wiki_view import render_mineral_wiki


logger = logging.getLogger(__name__)

st.title("Wiki de minerales")
st.caption("Fichas de referencia para los minerales de tu coleccion, ampliadas con Mindat.")

db = get_session()
try:
    query = st.text_input("Buscar mineral", placeholder="Nombre, formula, color, descripcion...")

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
        st.info("No hay minerales que coincidan con la busqueda.")
        st.stop()

    mineral_names = [mineral.name for mineral in minerals]
    default_name = st.session_state.get("selected_mineral_name")
    default_index = mineral_names.index(default_name) if default_name in mineral_names else 0
    selected_name = st.selectbox("Mineral", mineral_names, index=default_index)
    mineral = next(item for item in minerals if item.name == selected_name)

    c1, c2, c3 = st.columns(3)
    c1.metric("Piezas", len(mineral.items))
    c2.metric("Mindat ID", mineral.mindat_id or "-")
    c3.metric("Datos API", "Si" if mineral.api_raw_json else "No")

    if admin_unlocked() and st.button("Actualizar este mineral desde Mindat"):
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

    st.divider()
    render_mineral_wiki(mineral)

    if mineral.items:
        st.subheader("Piezas de tu coleccion")
        for item in mineral.items:
            label = f"{item.item_code} - {item.display_name or mineral.name}"
            if st.button(label, key=f"item_{item.id}"):
                st.session_state["selected_item_code"] = item.item_code
                st.switch_page("views/2_Ficha.py")

finally:
    db.close()
