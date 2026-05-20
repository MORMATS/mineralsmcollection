import streamlit as st

from src.db import init_db, get_session
from src.mindat_api import upsert_mindat_mineral, MindatConfigError
from src.settings import get_setting

st.set_page_config(page_title="Importar API", page_icon="🌐", layout="wide")
init_db()

st.title("Importar minerales desde Mindat API")
st.caption("Busca minerales por nombre y los guarda/actualiza en PostgreSQL.")

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

if st.button("Importar / actualizar"):
    names = [n.strip() for n in names_text.split(",") if n.strip()]
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
                                "sistema_cristalino": mineral.crystal_system,
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
