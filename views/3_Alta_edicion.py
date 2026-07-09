import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.auth import require_admin_access
from src.db import get_session, UPLOAD_DIR
from src.crud import delete_collection_item, generate_next_item_code
from src.item_types import ITEM_TYPE_LABELS, item_type_label, normalize_item_type
from src.item_images import move_image, normalize_image_order, ordered_images
from src.localities import get_or_create_locality, has_locality_data
from src.mindat_api import MindatConfigError, get_mindat_locality_data
from src.models import MineralSpecies, CollectionItem, ItemImage
from src.image_utils import ImageUploadError, save_uploaded_images
from src.ui import (
    render_page_header,
    render_section_heading,
    render_stable_photo,
    shared_image_frame_ratio,
)


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value or None


def format_coordinate(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}".rstrip("0").rstrip(".")


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

    needs_text = not any(clean_text(value) for value in (locality_name, mine, region, country))
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
    mindat_locality_id: int | None,
    locality_name: str,
    mine: str,
    region: str,
    country: str,
    latitude: float | None,
    longitude: float | None,
) -> None:
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
    apply_locality(db, item, mindat_locality_id, locality_name, mine, region, country, latitude, longitude)


def item_label(item: CollectionItem) -> str:
    return f"{item.item_code} - {item.display_name or item.mineral.name}"


def render_delete_item_panel(db, item: CollectionItem) -> None:
    with st.expander("Borrar pieza / anuncio"):
        st.warning("Esta accion borra la pieza de la base de datos y elimina sus fotos guardadas.")
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

render_page_header(
    "Administracion",
    "Alta / edicion",
    "Crea piezas nuevas o carga una pieza existente para modificar sus datos.",
    meta=["Piezas", "Fotos", "Inventario"],
)

if deleted_message := st.session_state.pop("item_deleted_message", None):
    st.success(deleted_message)
if delete_warnings := st.session_state.pop("item_delete_warnings", None):
    st.warning("La pieza se borro, pero algunas fotos no se pudieron eliminar:\n" + "\n".join(delete_warnings))

db = get_session()
try:
    minerals = db.execute(select(MineralSpecies).order_by(MineralSpecies.name)).scalars().all()
    mineral_names = [m.name for m in minerals]
    mineral_by_name = {m.name: m for m in minerals}

    if not mineral_names:
        st.warning("Primero crea o importa minerales desde Admin datos o Importar API.")
        st.stop()

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
    if editing:
        if not items:
            st.info("Todavia no hay piezas para editar.")
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

    next_item_code = generate_next_item_code(db)
    form_suffix = item.item_code if item else "new"
    default_mineral = item.mineral.name if item else mineral_names[0]
    default_mineral_index = mineral_names.index(default_mineral) if default_mineral in mineral_names else 0
    item_type_values = list(ITEM_TYPE_LABELS.keys())
    default_item_type = normalize_item_type(item.item_type if item else None)
    default_item_type_index = item_type_values.index(default_item_type)
    locality = item.locality if item else None

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
                value=item.display_name if item and item.display_name else "",
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
                value=item.secondary_minerals if item and item.secondary_minerals else "",
                key=f"secondary_{form_suffix}",
            )
            special_features = st.text_area(
                "Caracteristicas especiales",
                value=item.special_features if item and item.special_features else "",
                key=f"features_{form_suffix}",
            )
            sold = st.checkbox(
                "Vendido",
                value=bool(item.sold) if item else False,
                key=f"sold_{form_suffix}",
            )
            sold_at = (
                st.date_input(
                    "Fecha venta",
                    value=item.sold_at if item and item.sold_at else None,
                    key=f"sold_at_{form_suffix}",
                )
                if sold
                else None
            )
            purchase_link = st.text_input(
                "Link de compra / anuncio",
                value=item.purchase_link if item and item.purchase_link else "",
                key=f"purchase_link_{form_suffix}",
            )
        with c2:
            mindat_locality_id_text = st.text_input(
                "ID localidad Mindat",
                value=str(locality.mindat_locality_id) if locality and locality.mindat_locality_id else "",
                placeholder="Ej: 12345",
                key=f"mindat_locality_id_{form_suffix}",
            )
            country = st.text_input(
                "Pais",
                value=locality.country if locality and locality.country else "",
                key=f"country_{form_suffix}",
            )
            region = st.text_input(
                "Region",
                value=locality.region if locality and locality.region else "",
                key=f"region_{form_suffix}",
            )
            mine = st.text_input(
                "Mina / yacimiento",
                value=locality.mine if locality and locality.mine else "",
                key=f"mine_{form_suffix}",
            )
            locality_name = st.text_input(
                "Nombre localidad",
                value=locality.name if locality and locality.name else "",
                key=f"locality_{form_suffix}",
            )
            lat_col, lon_col = st.columns(2)
            latitude_text = lat_col.text_input(
                "Latitud",
                value=format_coordinate(locality.latitude) if locality else "",
                placeholder="Ej: 40.4168",
                key=f"latitude_{form_suffix}",
            )
            longitude_text = lon_col.text_input(
                "Longitud",
                value=format_coordinate(locality.longitude) if locality else "",
                placeholder="Ej: -3.7038",
                key=f"longitude_{form_suffix}",
            )
            acquisition_source = st.text_input(
                "Proveedor / origen adquisicion",
                value=item.acquisition_source if item and item.acquisition_source else "",
                key=f"source_{form_suffix}",
            )
            purchase_price = st.number_input(
                "Precio compra",
                min_value=0.0,
                step=1.0,
                value=float(item.purchase_price or 0.0) if item else 0.0,
                key=f"purchase_price_{form_suffix}",
            )
            sale_price = st.number_input(
                "Precio venta",
                min_value=0.0,
                step=1.0,
                value=float(item.sale_price or 0.0) if item else 0.0,
                key=f"sale_price_{form_suffix}",
            )
            notes = st.text_area(
                "Notas internas",
                value=item.notes if item and item.notes else "",
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
            st.success(f"Pieza {item.item_code} actualizada con {len(saved_paths)} foto(s) nueva(s).")
        else:
            saved_item_code = None
            saved_paths = []

            for attempt in range(3):
                try:
                    item_code = generate_next_item_code(db)
                    new_item = CollectionItem(item_code=item_code.strip(), sold=sold)
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
                    db.add(new_item)
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
                        st.error("No se pudo reservar un ID automatico. Vuelve a guardar la pieza.")
                        st.stop()
                except ImageUploadError as exc:
                    db.rollback()
                    st.error(str(exc))
                    st.stop()

            if saved_item_code:
                st.session_state["selected_item_code"] = saved_item_code
                st.session_state.pop("editing_item_code", None)
                st.success(f"Pieza {saved_item_code} guardada con {len(saved_paths)} foto(s).")
finally:
    db.close()
