import streamlit as st
from sqlalchemy import select

from src.db import init_db, get_session
from src.models import MineralSpecies, Locality, CollectionItem, ItemImage
from src.image_utils import save_uploaded_images

st.set_page_config(page_title="Alta / edicion", page_icon="➕", layout="wide")
init_db()

st.title("Alta de pieza y subida de fotos")

db = get_session()
try:
    minerals = db.execute(select(MineralSpecies).order_by(MineralSpecies.name)).scalars().all()
    mineral_names = [m.name for m in minerals]
    mineral_by_name = {m.name: m for m in minerals}

    if not mineral_names:
        st.warning("Primero crea o importa minerales desde Admin datos o Importar API.")
        st.stop()

    with st.form("new_item", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            item_code = st.text_input("ID unico de pieza", placeholder="MIN-0002")
            display_name = st.text_input("Nombre visible")
            mineral_name = st.selectbox("Mineral principal", mineral_names)
            secondary_minerals = st.text_area("Minerales secundarios")
            special_features = st.text_area("Caracteristicas especiales")
            sold = st.checkbox("Vendido")
            sold_at = st.date_input("Fecha venta", value=None) if sold else None
            purchase_link = st.text_input("Link de compra / anuncio")
        with c2:
            country = st.text_input("Pais")
            region = st.text_input("Region")
            mine = st.text_input("Mina / yacimiento")
            locality_name = st.text_input("Nombre localidad")
            acquisition_source = st.text_input("Proveedor / origen adquisicion")
            purchase_price = st.number_input("Precio compra", min_value=0.0, step=1.0)
            sale_price = st.number_input("Precio venta", min_value=0.0, step=1.0)
            notes = st.text_area("Notas internas")

        photos = st.file_uploader(
            "Fotos de la pieza",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )

        submitted = st.form_submit_button("Guardar pieza")

    if submitted:
        if not item_code:
            st.error("El ID es obligatorio.")
            st.stop()

        existing = db.execute(select(CollectionItem).where(CollectionItem.item_code == item_code)).scalar_one_or_none()
        if existing:
            st.error("Ya existe una pieza con ese ID.")
            st.stop()

        mineral = mineral_by_name[mineral_name]
        locality = Locality(
            name=locality_name or None,
            mine=mine or None,
            region=region or None,
            country=country or None,
        )
        db.add(locality)
        db.flush()

        item = CollectionItem(
            item_code=item_code.strip(),
            display_name=display_name or None,
            mineral=mineral,
            locality=locality,
            acquisition_source=acquisition_source or None,
            purchase_price=purchase_price or None,
            sale_price=sale_price or None,
            sold=sold,
            sold_at=sold_at if sold else None,
            purchase_link=purchase_link or None,
            special_features=special_features or None,
            secondary_minerals=secondary_minerals or None,
            notes=notes or None,
        )
        db.add(item)
        db.flush()

        paths = save_uploaded_images(item.item_code, photos)
        for i, path in enumerate(paths):
            db.add(ItemImage(item=item, file_path=path, is_cover=(i == 0)))

        db.commit()
        st.success(f"Pieza {item.item_code} guardada con {len(paths)} foto(s).")
finally:
    db.close()
