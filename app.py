import logging

import streamlit as st
from sqlalchemy import func, select

from src.auth import admin_unlocked, render_admin_sidebar
from src.db import get_session
from src.models import CollectionItem, MineralSpecies
from src.settings import is_production
from src.ui import render_global_styles


st.set_page_config(page_title="Minerales", page_icon=":gem:", layout="wide")
render_global_styles()
logger = logging.getLogger(__name__)


def home_page() -> None:
    st.title("Catalogo de minerales")
    st.caption("Coleccion y creaciones de Ismael Guessous. Para disfrutar y descubrir.")

    db = get_session()
    try:
        total_items = db.scalar(select(func.count(CollectionItem.id))) or 0
        total_minerals = db.scalar(select(func.count(MineralSpecies.id))) or 0
        sold_items = db.scalar(select(func.count(CollectionItem.id)).where(CollectionItem.sold == True)) or 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Piezas en coleccion", total_items)
        c2.metric("Minerales de referencia", total_minerals)
        c3.metric("Piezas vendidas", sold_items)

        st.subheader("Busqueda rapida")
        item_code = st.text_input("ID / codigo de pieza", placeholder="Ej: 12 o MIN-0012")
        if st.button("Abrir ficha") and item_code:
            st.session_state["selected_item_code"] = item_code.strip()
            st.switch_page("views/2_Ficha.py")
    finally:
        db.close()


public_pages = [
    st.Page(home_page, title="Inicio", icon=":material/home:", default=True),
    st.Page("views/1_Coleccion.py", title="Coleccion", icon=":material/grid_view:"),
    st.Page("views/2_Ficha.py", title="Ficha", icon=":material/search:"),
    st.Page("views/6_Wiki_minerales.py", title="Wiki minerales", icon=":material/menu_book:"),
]

admin_pages = [
    st.Page("views/3_Alta_edicion.py", title="Alta/edicion", icon=":material/add_circle:"),
    st.Page("views/4_Admin_datos.py", title="Admin datos", icon=":material/database:"),
    st.Page("views/5_Importar_API.py", title="Importar API", icon=":material/cloud_download:"),
]

pages = {"Catalogo": public_pages}
if admin_unlocked():
    pages["Administracion"] = admin_pages

selected_page = st.navigation(pages)
render_admin_sidebar()
try:
    selected_page.run()
except Exception:
    logger.exception("Unhandled application error")
    if is_production():
        st.error("No se pudo cargar esta vista. Revisa el servicio o intentalo de nuevo mas tarde.")
    else:
        raise
