from __future__ import annotations

import streamlit as st

from src.mineral_images import find_commons_mineral_image
from src.models import MineralSpecies
from src.wiki import extra_mindat_rows, mineral_description, mineral_wiki_sections


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def cached_commons_image(name: str) -> dict[str, str] | None:
    return find_commons_mineral_image(name)


def render_value(label: str, value: str) -> None:
    if label == "Fuente" and value.startswith("http"):
        st.write("**Fuente Mindat:**")
        st.link_button("Abrir ficha en Mindat", value)
        return

    if len(value) > 180:
        st.write(f"**{label}:**")
        st.write(value)
        return

    st.write(f"**{label}:** {value}")


def render_generic_photo(mineral_name: str) -> None:
    image = cached_commons_image(mineral_name)
    if not image:
        st.info("No he encontrado una foto generica libre para este mineral.")
        return

    st.image(image["thumbnail_url"], caption=image["caption"], width="stretch")
    st.link_button("Ver imagen y licencia", image["page_url"])


def render_mineral_wiki(mineral: MineralSpecies) -> None:
    left, right = st.columns([2, 1])

    with left:
        st.subheader(mineral.name)
        description = mineral_description(mineral)
        if description:
            st.write(description)

        for section, rows in mineral_wiki_sections(mineral).items():
            if not rows:
                continue
            st.markdown(f"#### {section}")
            for label, value in rows:
                render_value(label, value)

        extras = extra_mindat_rows(mineral)
        if extras:
            with st.expander("Otros datos importados"):
                for label, value in extras:
                    render_value(label, value)

    with right:
        st.markdown("#### Foto generica")
        render_generic_photo(mineral.name)
