import streamlit as st
from sqlalchemy import select, func

from src.db import init_db, get_session, get_database_url
from src.models import CollectionItem, MineralSpecies


st.set_page_config(page_title="Catalogo de Minerales", page_icon="💎", layout="wide")
init_db()

st.title("Catalogo / coleccion virtual de minerales")
st.caption("PostgreSQL en LXC Proxmox + Streamlit + Mindat API")

db = get_session()
try:
    total_items = db.scalar(select(func.count(CollectionItem.id))) or 0
    total_minerals = db.scalar(select(func.count(MineralSpecies.id))) or 0
    sold_items = db.scalar(select(func.count(CollectionItem.id)).where(CollectionItem.sold == True)) or 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Piezas en coleccion", total_items)
    c2.metric("Minerales de referencia", total_minerals)
    c3.metric("Vendidas", sold_items)

    with st.expander("Conexion actual"):
        safe_url = get_database_url()
        st.code(safe_url.split("@")[-1] if "@" in safe_url else safe_url)

    st.subheader("Busqueda rapida por ID")
    item_code = st.text_input("ID / codigo de pieza", placeholder="Ej: MIN-0001")
    if st.button("Abrir ficha") and item_code:
        st.session_state["selected_item_code"] = item_code.strip()
        st.switch_page("pages/2_Ficha.py")

    st.info("Usa la barra lateral para ir a Coleccion, Ficha, Alta/edicion, Admin datos o Importar API.")
finally:
    db.close()
