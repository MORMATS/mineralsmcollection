import streamlit as st

from src.db import init_db, get_session, UPLOAD_DIR
from src.crud import get_item_by_code

st.set_page_config(page_title="Ficha mineral", page_icon="🔎", layout="wide")
init_db()

st.title("Ficha de pieza")

default_code = st.session_state.get("selected_item_code", "")
item_code = st.text_input("ID de pieza", value=default_code, placeholder="Ej: MIN-0001")

db = get_session()
try:
    if item_code:
        item = get_item_by_code(db, item_code.strip())
        if not item:
            st.warning("No existe una pieza con ese ID.")
            st.stop()

        left, right = st.columns([1, 2])
        with left:
            if item.images:
                for img in item.images:
                    st.image(str(UPLOAD_DIR.parent / img.file_path), caption=img.caption, use_container_width=True)
            else:
                st.info("Esta pieza no tiene fotos.")

        with right:
            st.header(item.display_name or item.mineral.name)
            st.write(f"**ID:** {item.item_code}")
            st.write(f"**Mineral principal:** {item.mineral.name}")
            st.write(f"**Formula:** {item.mineral.formula or '-'}")
            st.write(f"**Sistema cristalino:** {item.mineral.crystal_system or '-'}")
            st.write(f"**Dureza:** {item.mineral.hardness_min or '-'} - {item.mineral.hardness_max or '-'}")
            st.write(f"**Color:** {item.mineral.color or '-'}")
            st.write(f"**Brillo:** {item.mineral.luster or '-'}")
            st.write(f"**Chakras:** {', '.join(c.name for c in item.mineral.chakras) or '-'}")
            st.write(f"**Zodiaco:** {', '.join(z.name for z in item.mineral.zodiac_signs) or '-'}")
            st.write(f"**Fuente API:** {item.mineral.source_url or '-'}")
            st.write(f"**Vendido:** {'Si' if item.sold else 'No'}")
            if item.purchase_link:
                st.link_button("Comprar / ver anuncio", item.purchase_link)

            if item.locality:
                st.subheader("Localidad")
                st.write(f"**Nombre:** {item.locality.name or '-'}")
                st.write(f"**Mina:** {item.locality.mine or '-'}")
                st.write(f"**Region:** {item.locality.region or '-'}")
                st.write(f"**Pais:** {item.locality.country or '-'}")

            st.subheader("Datos de indice")
            st.write(f"**Caracteristicas especiales:** {item.special_features or '-'}")
            st.write(f"**Minerales secundarios:** {item.secondary_minerals or '-'}")
            st.write(f"**Notas:** {item.notes or '-'}")
    else:
        st.info("Introduce un ID para buscar una pieza.")
finally:
    db.close()
