from __future__ import annotations

import logging

import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from src.auth import require_admin_access
from src.db import get_session
from src.item_types import item_type_label
from src.localities import (
    locality_coordinate_guess,
    locality_label,
    unmappable_reason,
    valid_coordinate,
)
from src.locality_editor import (
    LocalityValidationError,
    merge_mindat_locality_values,
    parse_locality_form,
)
from src.mindat_api import MindatConfigError, get_mindat_locality_data, update_mindat_locality
from src.models import CollectionItem, Locality
from src.navigation import switch_to_admin_edit
from src.ui import render_metric_cards, render_page_header, render_section_heading


logger = logging.getLogger(__name__)
require_admin_access()


def item_name(item: CollectionItem) -> str:
    return item.display_name or item.mineral.name


def locality_status(locality: Locality) -> str:
    coordinate = locality_coordinate_guess(locality)
    if coordinate:
        return coordinate.note
    return unmappable_reason(locality) or "Sin ubicación mapeable"


render_page_header(
    "Administración",
    "Localizaciones",
    "Ajusta los orígenes, sus coordenadas y las piezas vinculadas desde un único lugar.",
    meta=["Solo admin", "Coordenadas", "Piezas vinculadas"],
)

db = get_session()
try:
    localities = (
        db.execute(
            select(Locality)
            .options(selectinload(Locality.items).joinedload(CollectionItem.mineral))
            .order_by(Locality.country, Locality.region, Locality.mine, Locality.name, Locality.id)
        )
        .unique()
        .scalars()
        .all()
    )
    orphan_items = (
        db.execute(
            select(CollectionItem)
            .options(joinedload(CollectionItem.mineral))
            .where(CollectionItem.locality_id.is_(None))
            .order_by(CollectionItem.item_code)
        )
        .unique()
        .scalars()
        .all()
    )

    exact_count = sum(
        1 for locality in localities if valid_coordinate(locality.latitude, locality.longitude)
    )
    mapped_count = sum(1 for locality in localities if locality_coordinate_guess(locality))
    render_metric_cards(
        [
            ("Localizaciones", len(localities), "Orígenes reutilizables"),
            ("Exactas", exact_count, "Con latitud y longitud"),
            ("Aproximadas", mapped_count - exact_count, "Por localidad, región o país"),
            ("Con problemas", len(localities) - mapped_count + len(orphan_items), "Incluye piezas sin origen"),
        ]
    )

    if message := st.session_state.pop("locality_admin_message", None):
        st.success(message)

    editor_tab, overview_tab = st.tabs(["Editar o crear", "Diagnóstico y relaciones"])

    with editor_tab:
        mode = st.radio(
            "Acción",
            ["Editar existente", "Crear nueva"],
            horizontal=True,
            disabled=not localities,
        )
        selected = None
        if mode == "Editar existente" and localities:
            locality_ids = [locality.id for locality in localities]
            requested_id = st.session_state.pop("editing_locality_id", None)
            default_index = locality_ids.index(requested_id) if requested_id in locality_ids else 0
            selected_id = st.selectbox(
                "Localización",
                locality_ids,
                index=default_index,
                format_func=lambda locality_id: next(
                    f"{locality_label(locality)} · {len(locality.items)} pieza(s)"
                    for locality in localities
                    if locality.id == locality_id
                ),
            )
            selected = next(locality for locality in localities if locality.id == selected_id)

            coordinate = locality_coordinate_guess(selected)
            if coordinate:
                st.success(f"Mapeable: {coordinate.note} · {coordinate.latitude:.5f}, {coordinate.longitude:.5f}")
            else:
                st.warning(f"No mapeable: {unmappable_reason(selected)}")

            mineral_names = sorted({item.mineral.name for item in selected.items})
            st.caption(
                "Minerales o materiales vinculados: "
                + (", ".join(mineral_names) if mineral_names else "ninguno")
            )
            if selected.items:
                st.dataframe(
                    [
                        {
                            "Pieza": item.item_code,
                            "Nombre": item_name(item),
                            "Tipo": item_type_label(item.item_type),
                            "Mineral / material": item.mineral.name,
                        }
                        for item in selected.items
                    ],
                    hide_index=True,
                    use_container_width=True,
                )

            if selected.mindat_locality_id and st.button(
                "Actualizar esta localización desde Mindat",
                icon=":material/cloud_sync:",
                use_container_width=True,
            ):
                try:
                    _, update_message = update_mindat_locality(db, selected)
                    db.commit()
                except MindatConfigError as exc:
                    db.rollback()
                    st.error(str(exc))
                except Exception:
                    db.rollback()
                    logger.exception("Could not update locality %s from Mindat", selected.id)
                    st.error("No se pudo actualizar desde Mindat. Revisa la conexión y vuelve a intentarlo.")
                else:
                    st.session_state["locality_admin_message"] = update_message
                    st.rerun()

        form_locality = selected if mode == "Editar existente" else None
        with st.form(f"locality_editor_{form_locality.id if form_locality else 'new'}"):
            mindat_id = st.text_input(
                "ID de localidad en Mindat",
                value=str(form_locality.mindat_locality_id or "") if form_locality else "",
                help="Opcional. Debe ser único y mayor que cero.",
            )
            name_col, mine_col = st.columns(2)
            name = name_col.text_input("Localidad / municipio", value=form_locality.name or "" if form_locality else "")
            mine = mine_col.text_input("Mina / yacimiento", value=form_locality.mine or "" if form_locality else "")
            region_col, country_col = st.columns(2)
            region = region_col.text_input("Región", value=form_locality.region or "" if form_locality else "")
            country = country_col.text_input("País", value=form_locality.country or "" if form_locality else "")
            lat_col, lon_col = st.columns(2)
            latitude = lat_col.text_input(
                "Latitud",
                value=str(form_locality.latitude) if form_locality and form_locality.latitude is not None else "",
                placeholder="Ej.: 40.4168",
            )
            longitude = lon_col.text_input(
                "Longitud",
                value=str(form_locality.longitude) if form_locality and form_locality.longitude is not None else "",
                placeholder="Ej.: -3.7038",
            )
            source_url = st.text_input("Fuente / URL", value=form_locality.source_url or "" if form_locality else "")
            notes = st.text_area("Notas", value=form_locality.notes or "" if form_locality else "")
            submitted = st.form_submit_button(
                "Guardar cambios" if form_locality else "Crear localización",
                icon=":material/save:",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            refreshed_from_mindat = False
            try:
                values = parse_locality_form(
                    mindat_locality_id=mindat_id,
                    name=name,
                    mine=mine,
                    region=region,
                    country=country,
                    latitude=latitude,
                    longitude=longitude,
                    source_url=source_url,
                    notes=notes,
                )
                mindat_id_changed = bool(values["mindat_locality_id"]) and (
                    form_locality is None
                    or form_locality.mindat_locality_id != values["mindat_locality_id"]
                )
                if mindat_id_changed:
                    with st.spinner(f"Consultando Mindat {values['mindat_locality_id']}..."):
                        mindat_data = get_mindat_locality_data(values["mindat_locality_id"])
                    if not mindat_data:
                        raise LocalityValidationError(
                            f"Mindat no devolvió datos para la localidad {values['mindat_locality_id']}."
                        )
                    values = merge_mindat_locality_values(values, mindat_data)
                    refreshed_from_mindat = True

                conflict_query = select(Locality).where(
                    Locality.normalized_key == values["normalized_key"]
                )
                if form_locality:
                    conflict_query = conflict_query.where(Locality.id != form_locality.id)
                conflict = db.execute(conflict_query).scalar_one_or_none()
                if conflict:
                    raise LocalityValidationError(
                        f"Coincide con la localización #{conflict.id}: {locality_label(conflict)}."
                    )

                locality = form_locality or Locality()
                for field, value in values.items():
                    setattr(locality, field, value)
                if form_locality is None:
                    db.add(locality)
                db.commit()
            except LocalityValidationError as exc:
                db.rollback()
                st.error(str(exc))
            except MindatConfigError as exc:
                db.rollback()
                st.error(f"No se pudo actualizar la información desde Mindat: {exc}")
            except IntegrityError:
                db.rollback()
                st.error("Ya existe una localización con ese ID de Mindat o con los mismos datos.")
            except Exception:
                db.rollback()
                logger.exception("Could not save locality")
                st.error("No se pudo guardar la localización. Los cambios no se han aplicado.")
            else:
                st.session_state["editing_locality_id"] = locality.id
                st.session_state["locality_admin_message"] = (
                    "Localización guardada y actualizada desde Mindat."
                    if refreshed_from_mindat
                    else "Localización guardada correctamente."
                )
                st.rerun()

    with overview_tab:
        render_section_heading(
            "Estado de las localizaciones",
            "Filtra los problemas y comprueba qué minerales o materiales dependen de cada origen.",
        )
        problems_only = st.checkbox("Mostrar solo problemas", value=True)
        visible_localities = [
            locality
            for locality in localities
            if not problems_only or not locality_coordinate_guess(locality)
        ]
        if visible_localities:
            st.dataframe(
                [
                    {
                        "ID": locality.id,
                        "Origen": locality_label(locality),
                        "Estado del mapa": locality_status(locality),
                        "Coordenadas": (
                            f"{locality.latitude:.5f}, {locality.longitude:.5f}"
                            if valid_coordinate(locality.latitude, locality.longitude)
                            else ""
                        ),
                        "Piezas": len(locality.items),
                        "Minerales / materiales": ", ".join(
                            sorted({item.mineral.name for item in locality.items})
                        ),
                    }
                    for locality in visible_localities
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.success("No hay localizaciones con problemas de mapeo.")

        render_section_heading(
            "Piezas sin localización",
            "Estas piezas no pueden aparecer en el mapa hasta que se les asigne un origen.",
        )
        if orphan_items:
            st.dataframe(
                [
                    {
                        "Pieza": item.item_code,
                        "Nombre": item_name(item),
                        "Tipo": item_type_label(item.item_type),
                        "Mineral / material": item.mineral.name,
                    }
                    for item in orphan_items
                ],
                hide_index=True,
                use_container_width=True,
            )
            orphan_code = st.selectbox(
                "Pieza para completar",
                [item.item_code for item in orphan_items],
                format_func=lambda code: next(
                    f"{item.item_code} · {item_name(item)}" for item in orphan_items if item.item_code == code
                ),
            )
            if st.button("Editar pieza y asignar localización", use_container_width=True):
                switch_to_admin_edit(orphan_code)
        else:
            st.success("Todas las piezas tienen una localización asignada.")
finally:
    db.close()
