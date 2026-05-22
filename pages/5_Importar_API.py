import streamlit as st
from sqlalchemy import select

from src.db import init_db, get_session
from src.mindat_api import upsert_mindat_mineral, MindatConfigError
from src.models import CollectionItem, MineralSpecies
from src.settings import get_setting

st.set_page_config(page_title="Importar API", page_icon="🌐", layout="wide")
init_db()

st.title("Importar minerales desde Mindat API")
st.caption("Busca minerales por nombre, pide la ficha detallada si Mindat la expone y guarda el JSON completo.")

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
st.subheader("Actualizar wiki de mi coleccion")
st.write(f"{len(collection_names)} mineral(es) con piezas en la coleccion.")
if st.button("Actualizar minerales de mi coleccion desde Mindat", disabled=not collection_names):
    import_names(list(collection_names))
