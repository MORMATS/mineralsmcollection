import streamlit as st

from src.db import get_session, UPLOAD_DIR
from src.crud import get_item_by_code
from src.wiki import load_mindat_raw
from src.wiki_view import render_generic_photo, render_mineral_wiki

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
                st.caption("Foto generica del mineral")
                render_generic_photo(item.mineral.name)

        with right:
            st.header(item.display_name or item.mineral.name)
            st.write(f"**ID:** {item.item_code}")
            st.write(f"**Mineral principal:** {item.mineral.name}")
            st.write(f"**Vendido:** {'Si' if item.sold else 'No'}")
            if item.purchase_link:
                st.link_button("Comprar / ver anuncio", item.purchase_link)

        st.divider()
        ficha_tab, wiki_tab, api_tab = st.tabs(["Pieza", "Wiki mineral", "Datos Mindat"])

        with ficha_tab:
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

        with wiki_tab:
            chakra_names = ", ".join(c.name for c in item.mineral.chakras)
            zodiac_names = ", ".join(z.name for z in item.mineral.zodiac_signs)
            render_mineral_wiki(item.mineral)
            if chakra_names or zodiac_names:
                st.markdown("#### Asociaciones personales")
                st.write(f"**Chakras:** {chakra_names or '-'}")
                st.write(f"**Zodiaco:** {zodiac_names or '-'}")

        with api_tab:
            raw = load_mindat_raw(item.mineral)
            if raw:
                st.json(raw)
            else:
                st.info("Este mineral todavia no tiene JSON de Mindat guardado.")
    else:
        st.info("Introduce un ID para buscar una pieza.")
finally:
    db.close()
