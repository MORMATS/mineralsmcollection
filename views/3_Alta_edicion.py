import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.auth import require_admin_access
from src.db import get_session, UPLOAD_DIR
from src.crud import delete_collection_item, generate_next_item_code
from src.item_types import ITEM_TYPE_LABELS, item_type_label, normalize_item_type
from src.item_images import move_image, normalize_image_order, ordered_images
from src.localities import get_or_create_locality, has_locality_data, locality_label
from src.mindat_api import MindatConfigError, get_mindat_locality_data
from src.models import MineralSpecies, CollectionItem, ItemImage, Locality
from src.image_utils import ImageUploadError, save_uploaded_images
from src.ui import (
    render_page_header,
    render_section_heading,
    render_stable_photo,
    shared_image_frame_ratio,
)


NEW_LOCALITY_OPTION = "__new_locality__"
NO_LOCALITY_OPTION = "__no_locality__"
LOCALITY_OPTION_PREFIX = "locality:"
EMPTY_ITEM_TEMPLATE_OPTION = "__empty_item_template__"
NEW_ITEM_TEMPLATE_KEY = "new_item_template_choice"
RESET_NEW_ITEM_FORM_KEY = "reset_new_item_form"
NEW_ITEM_SAVED_MESSAGE_KEY = "new_item_saved_message"

NEW_ITEM_WIDGET_PREFIXES = (
    "item_code_new_",
    "display_name_new_",
    "item_type_new_",
    "mineral_new_",
    "secondary_new_",
    "features_new_",
    "sold_new_",
    "sold_at_new_",
    "purchase_link_new_",
    "mindat_locality_id_new_",
    "country_new_",
    "region_new_",
    "mine_new_",
    "locality_new_",
    "latitude_new_",
    "longitude_new_",
    "source_new_",
    "purchase_price_new_",
    "sale_price_new_",
    "notes_new_",
    "photos_new_",
    "locality_choice_new_",
    "pending_locality_choice_new_",
)


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value or None


def clear_new_item_form_state() -> None:
    keys_to_remove = [
        key
        for key in st.session_state
        if key == NEW_ITEM_TEMPLATE_KEY
        or any(str(key).startswith(prefix) for prefix in NEW_ITEM_WIDGET_PREFIXES)
    ]
    for key in keys_to_remove:
        st.session_state.pop(key, None)


def parse_coordinate(value: str, label: str, minimum: float, maximum: float) -> float | None:
    clean_value = clean_text(value)
    if clean_value is None:
        return None

    try:
        coordinate = float(clean_value.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"{label} debe ser un número válido.") from exc

    if coordinate < minimum or coordinate > maximum:
        raise ValueError(f"{label} debe estar entre {minimum:g} y {maximum:g}.")
    return coordinate


def parse_optional_positive_int(value: str, label: str) -> int | None:
    clean_value = clean_text(value)
    if clean_value is None:
        return None
    try:
        parsed = int(clean_value)
    except ValueError as exc:
        raise ValueError(f"{label} debe ser un numero entero positivo.") from exc
    if parsed <= 0:
        raise ValueError(f"{label} debe ser un numero entero positivo.")
    return parsed


def locality_option_value(locality_id: int) -> str:
    return f"{LOCALITY_OPTION_PREFIX}{locality_id}"


def locality_id_from_option(option: str) -> int | None:
    if not option.startswith(LOCALITY_OPTION_PREFIX):
        return None
    try:
        return int(option.removeprefix(LOCALITY_OPTION_PREFIX))
    except ValueError:
        return None


def locality_option_label(option: str, locality_by_id: dict[int, Locality]) -> str:
    if option == NEW_LOCALITY_OPTION:
        return "Añadir nueva localidad…"
    if option == NO_LOCALITY_OPTION:
        return "Sin localidad"

    locality_id = locality_id_from_option(option)
    if locality_id not in locality_by_id:
        return option
    locality = locality_by_id[locality_id]
    identifier = (
        f"Mindat {locality.mindat_locality_id}"
        if locality.mindat_locality_id
        else f"ID {locality.id}"
    )
    return f"{locality_label(locality)} · {identifier}"


def enrich_locality_from_mindat(
    mindat_locality_id: int | None,
    locality_name: str,
    mine: str,
    region: str,
    country: str,
    latitude: float | None,
    longitude: float | None,
) -> tuple[str, str, str, str, float | None, float | None]:
    if not mindat_locality_id:
        return locality_name, mine, region, country, latitude, longitude

    needs_text = any(
        not clean_text(value) for value in (locality_name, mine, region, country)
    )
    needs_coordinates = latitude is None or longitude is None
    if not needs_text and not needs_coordinates:
        return locality_name, mine, region, country, latitude, longitude

    try:
        data = get_mindat_locality_data(mindat_locality_id)
    except MindatConfigError:
        return locality_name, mine, region, country, latitude, longitude
    except Exception:
        st.warning("No se pudo consultar Mindat para esa localidad. Se guardaran los datos manuales.")
        return locality_name, mine, region, country, latitude, longitude

    if not data:
        return locality_name, mine, region, country, latitude, longitude

    return (
        locality_name or str(data.get("name") or ""),
        mine or str(data.get("mine") or ""),
        region or str(data.get("region") or ""),
        country or str(data.get("country") or ""),
        latitude if latitude is not None else data.get("latitude"),
        longitude if longitude is not None else data.get("longitude"),
    )


def apply_locality(
    db,
    item: CollectionItem,
    existing_locality: Locality | None,
    mindat_locality_id: int | None,
    locality_name: str,
    mine: str,
    region: str,
    country: str,
    latitude: float | None,
    longitude: float | None,
) -> None:
    if existing_locality is not None:
        item.locality = existing_locality
        return

    if not has_locality_data(locality_name, mine, region, country, latitude, longitude, mindat_locality_id):
        item.locality = None
        return

    item.locality = get_or_create_locality(
        db,
        mindat_locality_id=mindat_locality_id,
        name=locality_name,
        mine=mine,
        region=region,
        country=country,
        latitude=latitude,
        longitude=longitude,
    )


def apply_item_values(
    db,
    item: CollectionItem,
    mineral: MineralSpecies,
    item_type: str,
    display_name: str,
    secondary_minerals: str,
    special_features: str,
    sold: bool,
    sold_at,
    purchase_link: str,
    existing_locality: Locality | None,
    mindat_locality_id: int | None,
    locality_name: str,
    mine: str,
    region: str,
    country: str,
    latitude: float | None,
    longitude: float | None,
    acquisition_source: str,
    purchase_price: float,
    sale_price: float,
    notes: str,
) -> None:
    item.item_type = normalize_item_type(item_type)
    item.display_name = clean_text(display_name)
    item.mineral = mineral
    item.acquisition_source = clean_text(acquisition_source)
    item.purchase_price = purchase_price or None
    item.sale_price = sale_price or None
    item.sold = sold
    item.sold_at = sold_at if sold else None
    item.purchase_link = clean_text(purchase_link)
    item.special_features = clean_text(special_features)
    item.secondary_minerals = clean_text(secondary_minerals)
    item.notes = clean_text(notes)
    apply_locality(
        db,
        item,
        existing_locality,
        mindat_locality_id,
        locality_name,
        mine,
        region,
        country,
        latitude,
        longitude,
    )


def item_label(item: CollectionItem) -> str:
    return f"{item.item_code} - {item.display_name or item.mineral.name}"


def item_template_label(option: str, item_by_code: dict[str, CollectionItem]) -> str:
    if option == EMPTY_ITEM_TEMPLATE_OPTION:
        return "Empezar con el formulario vacio"

    item = item_by_code.get(option)
    if item is None:
        return option

    parts = [item_label(item)]
    if item.locality is not None:
        parts.append(locality_label(item.locality))
    return " · ".join(parts)


def render_delete_item_panel(db, item: CollectionItem) -> None:
    with st.expander("Borrar pieza / anuncio"):
        st.warning("Esta acción borra la pieza de la base de datos y elimina sus fotos guardadas.")
        confirm = st.checkbox(
            f"Confirmo que quiero borrar {item.item_code}",
            key=f"delete_confirm_{item.id}",
        )
        if st.button(
            "Borrar pieza y fotos",
            disabled=not confirm,
            key=f"delete_item_{item.id}",
        ):
            item_code = item.item_code
            try:
                deleted_count, delete_errors = delete_collection_item(db, item)
            except SQLAlchemyError:
                db.rollback()
                st.error("No se pudo borrar la pieza.")
                st.stop()

            st.session_state.pop("editing_item_code", None)
            if st.session_state.get("selected_item_code") == item_code:
                st.session_state.pop("selected_item_code", None)
            st.session_state["item_deleted_message"] = (
                f"Pieza {item_code} borrada. Fotos eliminadas: {deleted_count}."
            )
            if delete_errors:
                st.session_state["item_delete_warnings"] = delete_errors
            st.rerun()


def render_photo_order_editor(db, item: CollectionItem) -> None:
    images = ordered_images(item)
    if not images:
        return

    if any(
        getattr(image, "sort_order", None) != index or image.is_cover != (index == 1)
        for index, image in enumerate(images, 1)
    ):
        normalize_image_order(item)
        db.commit()
        images = ordered_images(item)

    render_section_heading(
        "Orden de fotos",
        "Ajusta la portada y la secuencia visual de la ficha.",
    )
    image_paths = [UPLOAD_DIR.parent / image.file_path for image in images]
    photo_frame_ratio = shared_image_frame_ratio(image_paths)

    for row_start in range(0, len(images), 4):
        cols = st.columns(4)
        for offset, image in enumerate(images[row_start : row_start + 4]):
            index = row_start + offset
            with cols[offset]:
                image_path = UPLOAD_DIR.parent / image.file_path
                if image_path.exists():
                    render_stable_photo(image_path, photo_frame_ratio)
                else:
                    st.warning("Archivo no encontrado.")
                st.caption(f"Foto {index + 1}{' - portada' if index == 0 else ''}")
                up_col, down_col = st.columns(2)
                if up_col.button("Subir", key=f"photo_up_{image.id}", disabled=index == 0):
                    move_image(item, image.id, -1)
                    db.commit()
                    st.rerun()
                if down_col.button(
                    "Bajar",
                    key=f"photo_down_{image.id}",
                    disabled=index == len(images) - 1,
                ):
                    move_image(item, image.id, 1)
                    db.commit()
                    st.rerun()


require_admin_access()

if st.session_state.pop(RESET_NEW_ITEM_FORM_KEY, False):
    clear_new_item_form_state()

render_page_header(
    "Administración",
    "Alta / edición",
    "Crea piezas nuevas o carga una pieza existente para modificar sus datos.",
    meta=["Piezas", "Fotos", "Inventario"],
)

if deleted_message := st.session_state.pop("item_deleted_message", None):
    st.success(deleted_message)
if delete_warnings := st.session_state.pop("item_delete_warnings", None):
    st.warning("La pieza se borro, pero algunas fotos no se pudieron eliminar:\n" + "\n".join(delete_warnings))
if updated_message := st.session_state.pop("item_updated_message", None):
    st.success(updated_message)
if saved_message := st.session_state.pop(NEW_ITEM_SAVED_MESSAGE_KEY, None):
    st.success(saved_message)

db = get_session()
try:
    minerals = db.execute(select(MineralSpecies).order_by(MineralSpecies.name)).scalars().all()
    mineral_names = [m.name for m in minerals]
    mineral_by_name = {m.name: m for m in minerals}

    if not mineral_names:
        st.warning("Primero crea o importa minerales desde Admin datos o Importar API.")
        st.stop()

    localities = (
        db.execute(
            select(Locality).order_by(
                Locality.country,
                Locality.region,
                Locality.mine,
                Locality.name,
                Locality.id,
            )
        )
        .scalars()
        .all()
    )
    locality_by_id = {
        locality.id: locality
        for locality in localities
        if locality.id is not None
    }

    items = (
        db.execute(
            select(CollectionItem)
            .options(
                joinedload(CollectionItem.mineral),
                joinedload(CollectionItem.locality),
                joinedload(CollectionItem.images),
            )
            .order_by(CollectionItem.created_at.desc())
        )
        .unique()
        .scalars()
        .all()
    )
    item_by_code = {existing_item.item_code: existing_item for existing_item in items}

    requested_edit_code = st.session_state.get("editing_item_code")
    default_mode = "Editar existente" if requested_edit_code and items else "Alta nueva"
    mode = st.radio(
        "Modo",
        ["Alta nueva", "Editar existente"],
        index=1 if default_mode == "Editar existente" else 0,
        horizontal=True,
    )
    editing = mode == "Editar existente"

    item = None
    template_item = None
    template_option = EMPTY_ITEM_TEMPLATE_OPTION
    if editing:
        if not items:
            st.info("Todavía no hay piezas para editar.")
            st.stop()

        item_codes = [existing_item.item_code for existing_item in items]
        default_index = item_codes.index(requested_edit_code) if requested_edit_code in item_codes else 0
        selected_code = st.selectbox(
            "Pieza a editar",
            item_codes,
            index=default_index,
            format_func=lambda code: item_label(next(existing for existing in items if existing.item_code == code)),
        )
        item = next(existing for existing in items if existing.item_code == selected_code)
        st.session_state["editing_item_code"] = item.item_code
        st.caption(f"Fotos actuales: {len(item.images)}. Puedes anadir mas fotos al guardar.")
        render_photo_order_editor(db, item)
    elif items:
        template_options = [EMPTY_ITEM_TEMPLATE_OPTION]
        template_options.extend(existing_item.item_code for existing_item in items)
        template_option = st.selectbox(
            "Rellenar desde una pieza anterior (opcional)",
            template_options,
            format_func=lambda option: item_template_label(option, item_by_code),
            key=NEW_ITEM_TEMPLATE_KEY,
            help=(
                "Copia los datos y la localidad de la pieza elegida. "
                "Podras cambiar cualquier campo antes de guardar; las fotos no se copian."
            ),
        )
        template_item = item_by_code.get(template_option)
        if template_item is not None:
            st.caption(
                f"Usando {template_item.item_code} como plantilla. "
                "Revisa los datos antes de guardar la nueva pieza."
            )

    next_item_code = generate_next_item_code(db)
    form_source = item if editing else template_item
    form_suffix = (
        item.item_code
        if item
        else f"new_{template_option}"
    )
    default_mineral = form_source.mineral.name if form_source else mineral_names[0]
    default_mineral_index = mineral_names.index(default_mineral) if default_mineral in mineral_names else 0
    item_type_values = list(ITEM_TYPE_LABELS.keys())
    default_item_type = normalize_item_type(form_source.item_type if form_source else None)
    default_item_type_index = item_type_values.index(default_item_type)

    locality_options = [NEW_LOCALITY_OPTION, NO_LOCALITY_OPTION]
    locality_options.extend(locality_option_value(locality_id) for locality_id in locality_by_id)
    if form_source and form_source.locality_id in locality_by_id:
        default_locality_option = locality_option_value(form_source.locality_id)
    elif form_source:
        default_locality_option = NO_LOCALITY_OPTION
    else:
        default_locality_option = NEW_LOCALITY_OPTION

    locality_choice_key = f"locality_choice_{form_suffix}"
    pending_locality_choice_key = f"pending_{locality_choice_key}"
    pending_locality_option = st.session_state.pop(pending_locality_choice_key, None)
    if pending_locality_option in locality_options:
        st.session_state[locality_choice_key] = pending_locality_option

    render_section_heading(
        "Localidad de la pieza",
        "Elige una localidad guardada o añade una nueva para reutilizarla en otras piezas.",
    )
    # Outside the form so changing the option immediately shows or hides the new-locality fields.
    locality_option = st.selectbox(
        "Localidad",
        locality_options,
        index=locality_options.index(default_locality_option),
        format_func=lambda option: locality_option_label(option, locality_by_id),
        key=locality_choice_key,
        help="Las localidades existentes se vinculan sin modificar sus datos.",
    )
    creating_locality = locality_option == NEW_LOCALITY_OPTION
    selected_locality_id = locality_id_from_option(locality_option)
    existing_locality = locality_by_id.get(selected_locality_id)

    with st.form(f"item_form_{form_suffix}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input(
                "ID de pieza",
                value=item.item_code if item else next_item_code,
                disabled=True,
                key=f"item_code_{form_suffix}",
            )
            display_name = st.text_input(
                "Nombre visible",
                value=form_source.display_name if form_source and form_source.display_name else "",
                key=f"display_name_{form_suffix}",
            )
            selected_item_type = st.selectbox(
                "Tipo de pieza",
                item_type_values,
                index=default_item_type_index,
                format_func=item_type_label,
                key=f"item_type_{form_suffix}",
            )
            mineral_name = st.selectbox(
                "Mineral principal",
                mineral_names,
                index=default_mineral_index,
                key=f"mineral_{form_suffix}",
            )
            secondary_minerals = st.text_area(
                "Minerales secundarios",
                value=(
                    form_source.secondary_minerals
                    if form_source and form_source.secondary_minerals
                    else ""
                ),
                key=f"secondary_{form_suffix}",
            )
            special_features = st.text_area(
                "Caracteristicas especiales",
                value=(
                    form_source.special_features
                    if form_source and form_source.special_features
                    else ""
                ),
                key=f"features_{form_suffix}",
            )
            sold = st.checkbox(
                "Vendido",
                value=bool(form_source.sold) if form_source else False,
                key=f"sold_{form_suffix}",
            )
            sold_at = (
                st.date_input(
                    "Fecha venta",
                    value=form_source.sold_at if form_source and form_source.sold_at else None,
                    key=f"sold_at_{form_suffix}",
                )
                if sold
                else None
            )
            purchase_link = st.text_input(
                "Link de compra / anuncio",
                value=form_source.purchase_link if form_source and form_source.purchase_link else "",
                key=f"purchase_link_{form_suffix}",
            )
        with c2:
            mindat_locality_id_text = ""
            country = ""
            region = ""
            mine = ""
            locality_name = ""
            latitude_text = ""
            longitude_text = ""

            if creating_locality:
                mindat_locality_id_text = st.text_input(
                    "ID localidad Mindat",
                    placeholder="Ej: 12345",
                    key=f"mindat_locality_id_{form_suffix}",
                )
                country = st.text_input(
                    "País",
                    key=f"country_{form_suffix}",
                )
                region = st.text_input(
                    "Región",
                    key=f"region_{form_suffix}",
                )
                mine = st.text_input(
                    "Mina / yacimiento",
                    key=f"mine_{form_suffix}",
                )
                locality_name = st.text_input(
                    "Nombre localidad",
                    key=f"locality_{form_suffix}",
                )
                lat_col, lon_col = st.columns(2)
                latitude_text = lat_col.text_input(
                    "Latitud",
                    placeholder="Ej: 40.4168",
                    key=f"latitude_{form_suffix}",
                )
                longitude_text = lon_col.text_input(
                    "Longitud",
                    placeholder="Ej: -3.7038",
                    key=f"longitude_{form_suffix}",
                )
            elif existing_locality is not None:
                st.info(f"Se usará: {locality_label(existing_locality)}")
            else:
                st.info("La pieza se guardará sin localidad.")

            acquisition_source = st.text_input(
                "Proveedor / origen adquisicion",
                value=(
                    form_source.acquisition_source
                    if form_source and form_source.acquisition_source
                    else ""
                ),
                key=f"source_{form_suffix}",
            )
            purchase_price = st.number_input(
                "Precio compra",
                min_value=0.0,
                step=1.0,
                value=float(form_source.purchase_price or 0.0) if form_source else 0.0,
                key=f"purchase_price_{form_suffix}",
            )
            sale_price = st.number_input(
                "Precio venta",
                min_value=0.0,
                step=1.0,
                value=float(form_source.sale_price or 0.0) if form_source else 0.0,
                key=f"sale_price_{form_suffix}",
            )
            notes = st.text_area(
                "Notas internas",
                value=form_source.notes if form_source and form_source.notes else "",
                key=f"notes_{form_suffix}",
            )

        photos = st.file_uploader(
            "Fotos nuevas de la pieza" if editing else "Fotos de la pieza",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"photos_{form_suffix}",
        )

        submitted = st.form_submit_button("Guardar cambios" if editing else "Guardar pieza")

    if editing and item:
        render_delete_item_panel(db, item)

    if submitted:
        mineral = mineral_by_name[mineral_name]
        mindat_locality_id = None
        latitude = None
        longitude = None

        if creating_locality:
            try:
                mindat_locality_id = parse_optional_positive_int(
                    mindat_locality_id_text,
                    "ID localidad Mindat",
                )
                latitude = parse_coordinate(latitude_text, "Latitud", -90, 90)
                longitude = parse_coordinate(longitude_text, "Longitud", -180, 180)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()
            locality_name, mine, region, country, latitude, longitude = enrich_locality_from_mindat(
                mindat_locality_id,
                locality_name,
                mine,
                region,
                country,
                latitude,
                longitude,
            )
            if (latitude is None) != (longitude is None):
                st.error("Para ubicar la pieza en el mapa, rellena latitud y longitud.")
                st.stop()

        if editing:
            if not item:
                st.error("Selecciona una pieza para editar.")
                st.stop()

            try:
                apply_item_values(
                    db,
                    item,
                    mineral,
                    selected_item_type,
                    display_name,
                    secondary_minerals,
                    special_features,
                    sold,
                    sold_at,
                    purchase_link,
                    existing_locality,
                    mindat_locality_id,
                    locality_name,
                    mine,
                    region,
                    country,
                    latitude,
                    longitude,
                    acquisition_source,
                    purchase_price,
                    sale_price,
                    notes,
                )
                current_images = ordered_images(item)
                saved_paths = save_uploaded_images(item.item_code, photos, start_index=len(item.images))
                for i, path in enumerate(saved_paths):
                    db.add(
                        ItemImage(
                            item=item,
                            file_path=path,
                            is_cover=False,
                            sort_order=len(current_images) + i + 1,
                        )
                    )
                normalize_image_order(item)

                db.commit()
            except IntegrityError:
                db.rollback()
                st.error("No se pudieron guardar los cambios por un conflicto de datos.")
                st.stop()
            except ImageUploadError as exc:
                db.rollback()
                st.error(str(exc))
                st.stop()

            st.session_state["selected_item_code"] = item.item_code
            st.session_state["editing_item_code"] = item.item_code
            updated_message = (
                f"Pieza {item.item_code} actualizada con {len(saved_paths)} foto(s) nueva(s)."
            )
            if creating_locality and item.locality_id:
                st.session_state[pending_locality_choice_key] = locality_option_value(
                    item.locality_id
                )
                st.session_state["item_updated_message"] = updated_message
                st.rerun()
            st.success(updated_message)
        else:
            saved_item_code = None
            saved_paths = []

            for attempt in range(3):
                try:
                    item_code = generate_next_item_code(db)
                    new_item = CollectionItem(item_code=item_code.strip(), sold=sold)
                    db.add(new_item)
                    apply_item_values(
                        db,
                        new_item,
                        mineral,
                        selected_item_type,
                        display_name,
                        secondary_minerals,
                        special_features,
                        sold,
                        sold_at,
                        purchase_link,
                        existing_locality,
                        mindat_locality_id,
                        locality_name,
                        mine,
                        region,
                        country,
                        latitude,
                        longitude,
                        acquisition_source,
                        purchase_price,
                        sale_price,
                        notes,
                    )
                    db.flush()

                    saved_paths = save_uploaded_images(new_item.item_code, photos)
                    for i, path in enumerate(saved_paths):
                        db.add(
                            ItemImage(
                                item=new_item,
                                file_path=path,
                                is_cover=(i == 0),
                                sort_order=i + 1,
                            )
                        )

                    db.commit()
                    saved_item_code = new_item.item_code
                    break
                except IntegrityError:
                    db.rollback()
                    if attempt == 2:
                        st.error("No se pudo reservar un ID automático. Vuelve a guardar la pieza.")
                        st.stop()
                except ImageUploadError as exc:
                    db.rollback()
                    st.error(str(exc))
                    st.stop()

            if saved_item_code:
                st.session_state["selected_item_code"] = saved_item_code
                st.session_state.pop("editing_item_code", None)
                st.session_state[NEW_ITEM_SAVED_MESSAGE_KEY] = (
                    f"Pieza {saved_item_code} guardada con {len(saved_paths)} foto(s). "
                    "El formulario ya esta listo para la siguiente alta."
                )
                st.session_state[RESET_NEW_ITEM_FORM_KEY] = True
                st.rerun()
finally:
    db.close()
