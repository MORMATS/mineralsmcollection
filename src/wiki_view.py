from __future__ import annotations

import streamlit as st

from src.mineral_images import find_commons_mineral_image
from src.models import MineralSpecies
from src.ui import escape_html, render_detail_grid, render_html, render_section_heading
from src.wiki import extra_mindat_rows, mineral_description, mineral_wiki_sections


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def cached_commons_image(name: str) -> dict[str, str] | None:
    return find_commons_mineral_image(name)


def render_value(label: str, value: str) -> None:
    if label == "Fuente" and value.startswith("http"):
        st.link_button("Abrir ficha en Mindat", value, use_container_width=True)
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

    render_html(
        f"""
        <article class="wiki-photo">
            <div class="wiki-photo-media" role="img" aria-label="{escape_html(image["caption"])}" style="--wiki-photo-url: url('{escape_html(image["thumbnail_url"])}');"></div>
            <div class="wiki-photo-body">
                <p class="wiki-photo-caption">{escape_html(image["caption"])}</p>
            </div>
        </article>
        """
    )
    st.link_button("Ver imagen y licencia", image["page_url"], use_container_width=True)


def render_wiki_rows(rows: list[tuple[str, str]]) -> None:
    regular_rows = [(label, value) for label, value in rows if label != "Fuente"]
    source_rows = [(label, value) for label, value in rows if label == "Fuente"]

    render_detail_grid(regular_rows)
    for _, value in source_rows:
        render_value("Fuente", value)


def render_mineral_wiki(mineral: MineralSpecies) -> None:
    left, right = st.columns([1.6, 1])

    with left:
        render_section_heading(mineral.name, "Referencia mineral enriquecida con datos externos cuando están disponibles.")
        description = mineral_description(mineral)
        if description:
            render_html(
                f"""
                <section class="info-panel">
                    <p>{escape_html(description)}</p>
                </section>
                """
            )

        for section, rows in mineral_wiki_sections(mineral).items():
            if not rows:
                continue
            st.markdown(f"#### {section}")
            render_wiki_rows(rows)

        extras = extra_mindat_rows(mineral)
        if extras:
            with st.expander("Otros datos importados"):
                render_wiki_rows(extras)

    with right:
        st.markdown("#### Foto genérica")
        render_generic_photo(mineral.name)
