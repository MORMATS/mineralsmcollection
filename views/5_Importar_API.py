import logging

import streamlit as st
from sqlalchemy import select

from src.auth import require_admin_access
from src.db import get_session
from src.mindat_api import upsert_mindat_mineral, MindatConfigError
from src.models import CollectionItem, MineralSpecies
from src.settings import get_setting
from src.settings import is_production
from src.ui import render_page_header, render_section_heading


logger = logging.getLogger(__name__)

require_admin_access()

render_page_header(
    "Administracion",
    "Importar Mindat",
    "Busca minerales por nombre y actualiza los datos utiles de la wiki si Mindat los expone.",
    meta=["Mindat API", "Wiki mineral", "Enriquecimiento"],
)

has_token = bool(get_setting("MINDAT_API_KEY", ""))
if has_token:
    st.success("MINDAT_API_KEY detectado.")
else:
    st.warning("No hay MINDAT_API_KEY. Configuralo en .env o .streamlit/secrets.toml.")

names_text = st.text_area(
    "Nombres de minerales",
    value="Quartz, Amethyst, Fluorite",
    help="Separados por comas. Ejemplo: Quartz, Amethyst, Fluorite",
)

def import_names(names: list[str]) -> None:
    if not names:
        st.error("Introduce al menos un nombre.")
        st.stop()

    db = get_session()
    try:
        for name in names:
            with st.spinner(f"Consultando Mindat: {name}"):
                try:
                    mineral, message = upsert_mindat_mineral(db, name)
                    if mineral:
                        st.success(message)
                        st.write(
                            {
                                "id_local": mineral.id,
                                "mindat_id": mineral.mindat_id,
                                "nombre": mineral.name,
                                "formula": mineral.formula,
                                "categoria": mineral.category,
                                "sistema_cristalino": mineral.crystal_system,
                                "color": mineral.color,
                                "brillo": mineral.luster,
                                "fuente": mineral.source_url,
                            }
                        )
                    else:
                        st.warning(message)
                except MindatConfigError as exc:
                    st.error(str(exc))
                    st.stop()
                except Exception as exc:
                    logger.exception("Error importing Mindat mineral %s", name)
                    if is_production():
                        st.error(f"Error importando {name}. Revisa los logs del servicio.")
                    else:
                        st.error(f"Error importando {name}: {exc}")
    finally:
        db.close()


manual_names = [n.strip() for n in names_text.split(",") if n.strip()]

if st.button("Importar / actualizar nombres"):
    import_names(manual_names)

db = get_session()
try:
    collection_names = (
        db.execute(
            select(MineralSpecies.name)
            .join(CollectionItem, CollectionItem.mineral_id == MineralSpecies.id)
            .distinct()
            .order_by(MineralSpecies.name)
        )
        .scalars()
        .all()
    )
finally:
    db.close()

st.divider()
render_section_heading(
    "Actualizar wiki de mi coleccion",
    "Recarga desde Mindat las especies que ya tienen piezas asociadas.",
)
st.write(f"{len(collection_names)} mineral(es) con piezas en la coleccion.")
if st.button("Actualizar minerales de mi coleccion desde Mindat", disabled=not collection_names):
    import_names(list(collection_names))
