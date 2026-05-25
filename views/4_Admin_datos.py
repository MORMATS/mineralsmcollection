import streamlit as st
from sqlalchemy import select

from src.auth import require_admin_access
from src.db import get_session
from src.models import MineralSpecies, Chakra, ZodiacSign
from src.seeds import seed_all

require_admin_access()

st.title("Admin de datos de referencia")

db = get_session()
try:
    if st.button("Cargar/recargar seed inicial"):
        seed_all(db)
        st.success("Seed cargado.")

    st.subheader("Crear mineral de referencia manualmente")
    with st.form("mineral"):
        name = st.text_input("Nombre mineral")
        formula = st.text_input("Formula")
        category = st.text_input("Categoria")
        crystal_system = st.text_input("Sistema cristalino")
        hardness_min = st.number_input("Dureza min", min_value=0.0, max_value=10.0, step=0.5)
        hardness_max = st.number_input("Dureza max", min_value=0.0, max_value=10.0, step=0.5)
        color = st.text_input("Color")
        luster = st.text_input("Brillo")
        description = st.text_area("Descripcion")
        chakras = db.execute(select(Chakra).order_by(Chakra.id)).scalars().all()
        zodiac = db.execute(select(ZodiacSign).order_by(ZodiacSign.id)).scalars().all()
        chakra_names = st.multiselect("Chakras", [c.name for c in chakras])
        zodiac_names = st.multiselect("Signos zodiaco", [z.name for z in zodiac])
        save = st.form_submit_button("Guardar mineral")

    if save:
        if not name:
            st.error("Nombre obligatorio.")
            st.stop()

        existing = db.execute(select(MineralSpecies).where(MineralSpecies.name == name)).scalar_one_or_none()
        if existing:
            st.error("Ya existe ese mineral.")
            st.stop()

        mineral = MineralSpecies(
            name=name,
            formula=formula or None,
            category=category or None,
            crystal_system=crystal_system or None,
            hardness_min=hardness_min or None,
            hardness_max=hardness_max or None,
            color=color or None,
            luster=luster or None,
            description=description or None,
        )
        mineral.chakras = [c for c in chakras if c.name in chakra_names]
        mineral.zodiac_signs = [z for z in zodiac if z.name in zodiac_names]
        db.add(mineral)
        db.commit()
        st.success("Mineral guardado.")
finally:
    db.close()
