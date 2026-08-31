from __future__ import annotations

from collections.abc import Iterable

import streamlit as st


COLLECTION_FILTERS_KEY = "collection_filter_params"


def collection_page():
    return st.Page(
        "views/1_Coleccion.py",
        title="Colección",
        icon=":material/grid_view:",
        url_path="coleccion",
    )


def map_page():
    return st.Page(
        "views/7_Mapa.py",
        title="Mapa",
        icon=":material/travel_explore:",
        url_path="mapa",
    )


def item_page():
    return st.Page(
        "views/2_Ficha.py",
        title="Ficha",
        icon=":material/search:",
        url_path="ficha",
    )


def wiki_page():
    return st.Page(
        "views/6_Wiki_minerales.py",
        title="Wiki minerales",
        icon=":material/menu_book:",
        url_path="wiki-minerales",
    )


def admin_edit_page():
    return st.Page(
        "views/3_Alta_edicion.py",
        title="Alta/edición",
        icon=":material/add_circle:",
        url_path="alta-edicion",
    )


def admin_data_page():
    return st.Page(
        "views/4_Admin_datos.py",
        title="Admin datos",
        icon=":material/database:",
        url_path="admin-datos",
    )


def admin_localities_page():
    return st.Page(
        "views/8_Localizaciones.py",
        title="Localizaciones",
        icon=":material/location_on:",
        url_path="localizaciones",
    )


def admin_import_page():
    return st.Page(
        "views/5_Importar_API.py",
        title="Importar API",
        icon=":material/cloud_download:",
        url_path="importar-api",
    )


def _query_value(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "")


def _locality_ids_text(locality_ids: Iterable[int] | str | None) -> str:
    if locality_ids is None:
        return ""
    if isinstance(locality_ids, str):
        return locality_ids
    return ",".join(str(locality_id) for locality_id in locality_ids)


def set_collection_filters(
    *,
    country: str | None = None,
    locality_ids: Iterable[int] | str | None = None,
    zone: str | None = None,
    item_type: str | None = None,
) -> None:
    filters = {
        "pais": country or "",
        "localidades": _locality_ids_text(locality_ids),
        "zona": zone or "",
        "tipo": item_type or "",
    }
    st.session_state[COLLECTION_FILTERS_KEY] = {
        key: value for key, value in filters.items() if value
    }


def collection_filters() -> dict[str, str]:
    filters = dict(st.session_state.get(COLLECTION_FILTERS_KEY, {}))
    for key in ("pais", "localidades", "zona", "tipo"):
        query_value = _query_value(key)
        if query_value:
            filters[key] = query_value
    return filters


def clear_collection_filters() -> None:
    st.session_state.pop(COLLECTION_FILTERS_KEY, None)


def switch_to_collection(
    *,
    country: str | None = None,
    locality_ids: Iterable[int] | str | None = None,
    zone: str | None = None,
    item_type: str | None = None,
) -> None:
    if country or locality_ids or zone or item_type:
        set_collection_filters(
            country=country,
            locality_ids=locality_ids,
            zone=zone,
            item_type=item_type,
        )
    st.switch_page(collection_page())


def switch_to_item(item_code: str) -> None:
    st.session_state["selected_item_code"] = item_code
    st.switch_page(item_page())


def switch_to_admin_edit(item_code: str | None = None) -> None:
    if item_code:
        st.session_state["editing_item_code"] = item_code
    st.switch_page(admin_edit_page())


def switch_to_admin_localities(locality_id: int | None = None) -> None:
    if locality_id:
        st.session_state["editing_locality_id"] = locality_id
    st.switch_page(admin_localities_page())
