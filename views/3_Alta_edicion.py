import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.auth import require_admin_access
from src.db import get_session
from src.crud import generate_next_item_code
from src.models import MineralSpecies, Locality, CollectionItem, ItemImage
from src.image_utils import ImageUploadError, save_uploaded_images

require_admin_access()

st.title("Alta de pieza y subida de fotos")
st.caption("El ID de pieza se genera automaticamente al guardar.")

db = get_session()
try:
    minerals = db.execute(select(MineralSpecies).order_by(MineralSpecies.name)).scalars().all()
    mineral_names = [m.name for m in minerals]
    mineral_by_name = {m.name: m for m in minerals}

    if not mineral_names:
        st.warning("Primero crea o importa minerales desde Admin datos o Importar API.")
        st.stop()

    next_item_code = generate_next_item_code(db)

    with st.form("new_item", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("ID automatico de pieza", value=next_item_code, disabled=True)
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
        mineral = mineral_by_name[mineral_name]
        saved_item_code = None
        saved_paths = []

        for attempt in range(3):
            try:
                item_code = generate_next_item_code(db)
                has_locality = any([locality_name, mine, region, country])
                locality = None
                if has_locality:
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

                saved_paths = save_uploaded_images(item.item_code, photos)
                for i, path in enumerate(saved_paths):
                    db.add(ItemImage(item=item, file_path=path, is_cover=(i == 0)))

                db.commit()
                saved_item_code = item.item_code
                break
            except IntegrityError:
                db.rollback()
                if attempt == 2:
                    st.error("No se pudo reservar un ID automatico. Vuelve a guardar la pieza.")
                    st.stop()
            except ImageUploadError as exc:
                db.rollback()
                st.error(str(exc))
                st.stop()

        if saved_item_code:
            st.success(f"Pieza {saved_item_code} guardada con {len(saved_paths)} foto(s).")
finally:
    db.close()
