import pandas as pd
import streamlit as st

from src.db import get_session, UPLOAD_DIR
from src.crud import list_collection_items, option_lists

st.title("Coleccion completa")
db = get_session()

try:
    opts = option_lists(db)

    with st.sidebar:
        st.header("Filtros")
        text = st.text_input("Buscar texto o ID")
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

    st.write(f"{len(items)} pieza(s) encontradas")

    rows = []
    for item in items:
        rows.append(
            {
                "ID": item.item_code,
                "Nombre": item.display_name or item.mineral.name,
                "Mineral": item.mineral.name,
                "Formula": item.mineral.formula or "",
                "Sistema": item.mineral.crystal_system or "",
                "Vendido": "Si" if item.sold else "No",
                "Pais": item.locality.country if item.locality else "",
                "Region": item.locality.region if item.locality else "",
                "Chakras": ", ".join(c.name for c in item.mineral.chakras),
                "Minerales secundarios": item.secondary_minerals or "",
                "Caracteristicas especiales": item.special_features or "",
                "Link compra": item.purchase_link or "",
            }
        )

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={"Link compra": st.column_config.LinkColumn("Link compra")},
        )

    st.divider()

    for item in items:
        cover = next((img for img in item.images if img.is_cover), item.images[0] if item.images else None)
        cols = st.columns([1, 3])
        with cols[0]:
            if cover:
                st.image(str(UPLOAD_DIR.parent / cover.file_path), use_container_width=True)
            else:
                st.write("Sin foto")
        with cols[1]:
            st.subheader(f"{item.item_code} - {item.display_name or item.mineral.name}")
            st.write(f"**Mineral:** {item.mineral.name}")
            st.write(f"**Estado:** {'Vendido' if item.sold else 'Disponible'}")
            if item.locality:
                loc = ", ".join(x for x in [item.locality.mine, item.locality.region, item.locality.country] if x)
                st.write(f"**Ubicacion:** {loc}")
            if item.special_features:
                st.write(f"**Caracteristicas:** {item.special_features}")
            if item.secondary_minerals:
                st.write(f"**Minerales secundarios:** {item.secondary_minerals}")
            if item.purchase_link:
                st.link_button("Comprar / ver anuncio", item.purchase_link)
            if st.button("Ver ficha", key=f"open_{item.id}"):
                st.session_state["selected_item_code"] = item.item_code
                st.switch_page("views/2_Ficha.py")
            if st.button("Ver wiki mineral", key=f"wiki_{item.id}"):
                st.session_state["selected_mineral_name"] = item.mineral.name
                st.switch_page("views/6_Wiki_minerales.py")
finally:
    db.close()
