import streamlit as st

from src.auth import admin_unlocked
from src.db import get_session, UPLOAD_DIR
from src.crud import get_item_by_code, normalize_item_code
from src.item_images import ordered_images
from src.ui import max_image_height_ratio, render_stable_photo
from src.wiki_view import render_generic_photo, render_mineral_wiki


def move_photo(key: str, count: int, delta: int) -> None:
    current = int(st.session_state.get(key, 0))
    st.session_state[key] = (current + delta) % count


def clean_display(value) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    return value


def visible_rows(rows: list[tuple[str, object]]) -> list[tuple[str, str]]:
    result = []
    for label, value in rows:
        display_value = clean_display(value)
        if display_value:
            result.append((label, display_value))
    return result


def render_visible_section(title: str, rows: list[tuple[str, str]]) -> None:
    st.markdown(f"#### {title}")
    for label, value in rows:
        st.write(f"**{label}:** {value}")


def render_optional_section(title: str, rows: list[tuple[str, object]]) -> bool:
    visible = visible_rows(rows)
    if not visible:
        return False

    render_visible_section(title, visible)
    return True


def render_item_details(item) -> bool:
    sections = []
    if item.locality:
        locality_rows = visible_rows(
            [
                ("Nombre", item.locality.name),
                ("Mina", item.locality.mine),
                ("Region", item.locality.region),
                ("Pais", item.locality.country),
            ]
        )
        if locality_rows:
            sections.append(("Localidad", locality_rows))

    index_rows = visible_rows(
        [
            ("Caracteristicas especiales", item.special_features),
            ("Minerales secundarios", item.secondary_minerals),
            ("Notas", item.notes),
        ]
    )
    if index_rows:
        sections.append(("Datos de indice", index_rows))

    if not sections:
        return False

    st.subheader("Datos de pieza")
    for title, rows in sections:
        render_visible_section(title, rows)
    return True


def render_item_photos(item) -> None:
    images = [
        image
        for image in ordered_images(item)
        if (UPLOAD_DIR.parent / image.file_path).exists()
    ]
    image_paths = [UPLOAD_DIR.parent / image.file_path for image in images]
    photo_frame_ratio = max_image_height_ratio(image_paths)

    if not images:
        st.info("Esta pieza no tiene fotos.")
        st.caption("Foto generica del mineral")
        render_generic_photo(item.mineral.name)
        return

    state_key = f"photo_index_{item.item_code}"
    try:
        current = int(st.session_state.get(state_key, 0))
    except (TypeError, ValueError):
        current = 0
    current = max(0, min(current, len(images) - 1))
    st.session_state[state_key] = current

    image = images[current]
    render_stable_photo(
        UPLOAD_DIR.parent / image.file_path,
        photo_frame_ratio,
        caption=image.caption,
    )

    if len(images) == 1:
        st.caption("Foto 1 de 1")
        return

    previous_col, count_col, next_col = st.columns([1, 2, 1])
    previous_col.button(
        "<",
        key=f"{state_key}_previous",
        help="Foto anterior",
        on_click=move_photo,
        args=(state_key, len(images), -1),
    )
    count_col.caption(f"Foto {current + 1} de {len(images)}")
    next_col.button(
        ">",
        key=f"{state_key}_next",
        help="Foto siguiente",
        on_click=move_photo,
        args=(state_key, len(images), 1),
    )


st.title("Ficha de pieza")

query_code = st.query_params.get("pieza")
default_code = normalize_item_code(query_code) if query_code else st.session_state.get("selected_item_code", "")
with st.form("item_lookup"):
    typed_code = st.text_input("ID de pieza", value=default_code, placeholder="Ej: 1 o MIN-0001")
    lookup_submitted = st.form_submit_button("Buscar")

if lookup_submitted and typed_code:
    st.session_state["selected_item_code"] = normalize_item_code(typed_code)
    st.rerun()

item_code = normalize_item_code(query_code or st.session_state.get("selected_item_code", typed_code))

db = get_session()
try:
    if item_code:
        item = get_item_by_code(db, item_code.strip())
        if not item:
            st.warning("No existe una pieza con ese ID.")
            st.stop()

        st.header(item.display_name or item.mineral.name)
        c1, c2, c3 = st.columns(3)
        c1.write(f"**ID:** {item.item_code}")
        c2.write(f"**Mineral principal:** {item.mineral.name}")
        c3.write(f"**Vendido:** {'Si' if item.sold else 'No'}")

        action_cols = st.columns([1, 1, 4])
        if item.purchase_link:
            action_cols[0].link_button("Comprar / ver anuncio", item.purchase_link)
        if admin_unlocked() and action_cols[1].button("Editar pieza"):
            st.session_state["editing_item_code"] = item.item_code
            st.switch_page("views/3_Alta_edicion.py")

        pieza_tab, wiki_tab = st.tabs(["Pieza", "Wiki mineral"])

        with pieza_tab:
            left, right = st.columns([1, 2])
            with left:
                render_item_photos(item)

            with right:
                render_item_details(item)

        with wiki_tab:
            chakra_names = ", ".join(c.name for c in item.mineral.chakras)
            zodiac_names = ", ".join(z.name for z in item.mineral.zodiac_signs)
            render_mineral_wiki(item.mineral)
            render_optional_section(
                "Asociaciones personales",
                [
                    ("Chakras", chakra_names),
                    ("Zodiaco", zodiac_names),
                ],
            )
    else:
        st.info("Introduce un ID para buscar una pieza.")
finally:
    db.close()
