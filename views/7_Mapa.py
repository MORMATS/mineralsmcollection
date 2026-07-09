from __future__ import annotations

import base64
from collections import OrderedDict
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlencode

import streamlit as st
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from src.crud import list_collection_items, option_lists
from src.db import UPLOAD_DIR, get_session
from src.item_images import ordered_images
from src.item_types import (
    ITEM_TYPE_FILTER_ALL,
    item_type_from_filter,
    item_type_label,
    normalize_item_type,
)
from src.localities import locality_coordinate_guess, locality_label, locality_normalized_key, normalized_text_key
from src.navigation import switch_to_collection, switch_to_item
from src.ui import escape_html, render_html, render_metric_cards, render_page_header, render_section_heading


WORLD_MAP_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" preserveAspectRatio="none">
  <defs>
    <linearGradient id="ocean" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#dbe8ee"/>
      <stop offset="1" stop-color="#c7d9e1"/>
    </linearGradient>
    <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#153a5b" flood-opacity=".14"/>
    </filter>
  </defs>
  <rect width="1000" height="500" fill="url(#ocean)"/>
  <g fill="none" stroke="#fffaf2" stroke-width="1" opacity=".38">
    <path d="M0 125H1000M0 250H1000M0 375H1000"/>
    <path d="M125 0V500M250 0V500M375 0V500M500 0V500M625 0V500M750 0V500M875 0V500"/>
  </g>
  <g filter="url(#softShadow)" fill="#d5bf99" stroke="#8f764e" stroke-width="2.4" stroke-linejoin="round">
    <path d="M74 138 C120 92 189 72 248 89 C282 100 313 126 329 156 C307 167 281 171 260 192 C236 216 232 251 205 268 C174 288 130 274 111 245 C94 220 95 190 74 138Z"/>
    <path d="M251 262 C289 272 318 303 316 343 C314 390 281 432 256 475 C220 426 199 382 209 336 C217 300 228 278 251 262Z"/>
    <path d="M411 133 C448 101 509 90 568 110 C620 128 676 120 726 137 C779 154 828 187 870 222 C838 249 776 256 721 242 C679 231 646 250 607 242 C565 235 535 201 493 199 C457 197 419 188 396 163 C386 151 392 142 411 133Z"/>
    <path d="M503 210 C543 205 580 231 594 273 C606 312 587 354 559 397 C526 360 493 318 488 278 C485 249 490 226 503 210Z"/>
    <path d="M802 321 C838 303 881 312 910 340 C895 372 856 387 818 374 C795 366 787 341 802 321Z"/>
    <path d="M889 414 C909 405 930 411 940 428 C925 443 901 445 884 434 C875 427 879 419 889 414Z"/>
    <path d="M462 124 C481 114 506 116 522 132 C502 145 476 145 462 124Z"/>
    <path d="M302 112 C321 101 345 105 359 122 C341 136 316 133 302 112Z"/>
  </g>
</svg>
"""


def world_map_data_uri() -> str:
    return f"data:image/svg+xml;charset=utf-8,{quote(WORLD_MAP_SVG)}"


class LocationGroup:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        label: str,
        filter_kind: str,
        filter_value: str,
        coordinate_note: str,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.label = label
        self.filter_kind = filter_kind
        self.filter_value = filter_value
        self.coordinate_note = coordinate_note
        self.items = []


def item_label(item) -> str:
    return item.display_name or item.mineral.name


def cover_image_path(item) -> Path | None:
    for image in ordered_images(item):
        path = UPLOAD_DIR.parent / image.file_path
        if path.exists():
            return path
    return None


def group_items_by_location(items) -> tuple[list[LocationGroup], int]:
    groups: OrderedDict[tuple, LocationGroup] = OrderedDict()
    missing_coordinates = 0

    for item in items:
        locality = item.locality
        coordinate = locality_coordinate_guess(locality)
        if not coordinate:
            missing_coordinates += 1
            continue

        latitude = coordinate.latitude
        longitude = coordinate.longitude
        locality_key = (
            locality_normalized_key(
                mindat_locality_id=locality.mindat_locality_id,
                name=locality.name,
                mine=locality.mine,
                region=locality.region,
                country=locality.country,
                latitude=locality.latitude,
                longitude=locality.longitude,
            )
            if locality
            else None
        )
        if locality and locality_key and coordinate.note != "Aproximado por pais":
            key = ("location", locality_key)
            label = locality_label(locality)
            filter_kind = "location"
            filter_value = ""
        elif locality and locality.country:
            key = ("country", normalized_text_key(locality.country))
            label = locality.country
            filter_kind = "country"
            filter_value = locality.country
        else:
            key = ("coordinate", round(latitude, 4), round(longitude, 4))
            label = locality_label(locality)
            filter_kind = "location"
            filter_value = ""

        if key not in groups:
            groups[key] = LocationGroup(
                latitude=latitude,
                longitude=longitude,
                label=label,
                filter_kind=filter_kind,
                filter_value=filter_value,
                coordinate_note=coordinate.note,
            )
        groups[key].items.append(item)

    return list(groups.values()), missing_coordinates


def item_type_summary(items: list) -> str:
    item_types = {normalize_item_type(item.item_type) for item in items}
    if len(item_types) == 1:
        return item_type_label(next(iter(item_types)))
    return "Mixto"


def mineral_summary(items: list, limit: int = 3) -> str:
    names = []
    for item in items:
        if item.mineral.name not in names:
            names.append(item.mineral.name)
    visible_names = names[:limit]
    suffix = f" +{len(names) - limit}" if len(names) > limit else ""
    return ", ".join(visible_names) + suffix


def locality_ids_text(items: list) -> str:
    ids = sorted({item.locality_id for item in items if item.locality_id})
    return ",".join(str(locality_id) for locality_id in ids)


def marker_color(item_type: str | None) -> tuple[int, int, int]:
    normalized = normalize_item_type(item_type)
    if normalized == "pendant":
        return (143, 96, 34)
    return (21, 58, 91)


@st.cache_data(show_spinner=False)
def _photo_icon_data_uri(path_text: str, mtime_ns: int, item_type: str | None) -> str | None:
    path = Path(path_text)
    try:
        image = Image.open(path).convert("RGB")
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return None

    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS

    image = ImageOps.fit(image, (128, 128), method=resample)
    canvas = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
    mask = Image.new("L", (128, 128), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 127, 127), fill=255)
    canvas.paste(image, (11, 11), mask)

    ring = marker_color(item_type)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((7, 7, 142, 142), outline=(*ring, 255), width=7)
    draw.ellipse((15, 15, 134, 134), outline=(255, 250, 242, 245), width=3)

    output = BytesIO()
    canvas.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def fallback_icon_data_uri(title: str, item_type: str | None) -> str:
    initial = "?"
    for character in title.strip():
        if character.isalnum():
            initial = character.upper()
            break

    ring = marker_color(item_type)
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="150" height="150" viewBox="0 0 150 150">
      <circle cx="75" cy="75" r="68" fill="#fffaf2" stroke="rgb({ring[0]}, {ring[1]}, {ring[2]})" stroke-width="7"/>
      <circle cx="75" cy="75" r="56" fill="#ede8de" stroke="#fffaf2" stroke-width="3"/>
      <text x="75" y="85" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="56" font-weight="800" fill="rgb({ring[0]}, {ring[1]}, {ring[2]})">{initial}</text>
    </svg>
    """
    return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


def icon_data_for_item(item) -> dict:
    cover_path = cover_image_path(item)
    icon_url = None
    if cover_path:
        icon_url = _photo_icon_data_uri(str(cover_path), cover_path.stat().st_mtime_ns, item.item_type)
    if not icon_url:
        icon_url = fallback_icon_data_uri(item_label(item), item.item_type)
    return {"url": icon_url, "width": 150, "height": 150, "anchorX": 75, "anchorY": 75}


def build_marker_rows(groups: list[LocationGroup]) -> tuple[list[dict], list[dict]]:
    single_rows = []
    bubble_rows = []

    for group in groups:
        items = sorted(group.items, key=lambda item: item.created_at, reverse=True)
        first_item = items[0]
        count = len(items)
        base_row = {
            "latitude": group.latitude,
            "longitude": group.longitude,
            "label": group.label,
            "count": count,
            "count_text": str(count),
            "type_label": item_type_summary(items),
            "minerals": mineral_summary(items),
            "item_codes": ", ".join(item.item_code for item in items[:4]),
            "coordinate_note": group.coordinate_note,
        }

        if count == 1:
            base_row.update(
                {
                    "target_kind": "item",
                    "target_value": first_item.item_code,
                    "action": "Abrir ficha",
                    "icon_data": icon_data_for_item(first_item),
                    "title": item_label(first_item),
                }
            )
            single_rows.append(base_row)
        else:
            target_kind = group.filter_kind
            target_value = (
                locality_ids_text(items)
                if group.filter_kind == "location"
                else group.filter_value
            )
            base_row.update(
                {
                    "target_kind": target_kind,
                    "target_value": target_value,
                    "action": "Ver piezas filtradas",
                    "radius_meters": 36000 + min(count, 12) * 4200,
                }
            )
            bubble_rows.append(base_row)

    return single_rows, bubble_rows


def projected_position(row: dict) -> tuple[float, float]:
    longitude = min(max(float(row["longitude"]), -180), 180)
    latitude = min(max(float(row["latitude"]), -82), 85)
    x = (longitude + 180) / 360 * 100
    y = (90 - latitude) / 180 * 100
    return min(max(x, 3), 97), min(max(y, 5), 95)


def map_marker_href(row: dict, selected_item_type: str | None) -> str:
    params = {"map_zona": row["label"]}
    if row["target_kind"] == "item":
        params["map_item"] = row["target_value"]
    elif row["target_kind"] == "country":
        params["map_pais"] = row["target_value"]
    else:
        params["map_localidades"] = row["target_value"]
    if selected_item_type:
        params["map_tipo"] = selected_item_type
    return "/?" + urlencode(params)


def render_map(single_rows: list[dict], bubble_rows: list[dict], selected_item_type: str | None) -> None:
    rows = [*bubble_rows, *single_rows]
    markers = []
    world_map = world_map_data_uri()

    for row in rows:
        x, y = projected_position(row)
        href = map_marker_href(row, selected_item_type)
        title = (
            f"{row['label']} · {row['count']} pieza(s) · "
            f"{row['type_label']} · {row['coordinate_note']}"
        )
        if row["target_kind"] == "item":
            image_url = row["icon_data"]["url"]
            marker_inner = (
                f'<span class="atlas-photo" style="background-image: url({escape_html(image_url)});"></span>'
            )
            marker_class = "is-photo"
        else:
            marker_inner = f'<span class="atlas-count">{escape_html(row["count_text"])}</span>'
            marker_class = "is-bubble"

        markers.append(
            f'<a class="atlas-marker {marker_class}" href="{escape_html(href)}" '
            f'style="left:{x:.3f}%; top:{y:.3f}%;" title="{escape_html(title)}">'
            f'{marker_inner}<span class="atlas-label">{escape_html(row["label"])}</span></a>'
        )

    render_html(
        f"""
        <style>
        .atlas-map {{
            position: relative;
            aspect-ratio: 2 / 1;
            min-height: 420px;
            margin: .8rem 0 1.1rem;
            overflow: hidden;
            border: 1px solid var(--m4w-border);
            border-radius: 8px;
            background: #dbe8ee;
            box-shadow: var(--m4w-shadow-soft);
        }}

        .atlas-world-map {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: fill;
            filter: saturate(.98) contrast(1.02);
            pointer-events: none;
            user-select: none;
        }}

        .atlas-map::after {{
            content: "Mapa del mundo · clic en burbuja o foto";
            position: absolute;
            left: 1rem;
            bottom: .85rem;
            padding: .35rem .55rem;
            border: 1px solid rgba(21,58,91,.18);
            border-radius: 8px;
            background: rgba(255,250,242,.86);
            color: var(--m4w-text-light);
            font-size: .78rem;
            font-weight: 750;
        }}

        .atlas-marker {{
            position: absolute;
            z-index: 2;
            display: grid;
            place-items: center;
            width: 4.4rem;
            height: 4.4rem;
            transform: translate(-50%, -50%);
            color: #fffaf2;
            text-decoration: none;
            transition: transform .16s ease, filter .16s ease;
        }}

        .atlas-marker:hover {{
            transform: translate(-50%, -50%) scale(1.07);
            filter: saturate(1.08) contrast(1.04);
        }}

        .atlas-count,
        .atlas-photo {{
            display: grid;
            place-items: center;
            width: 3.65rem;
            height: 3.65rem;
            border: 4px solid rgba(255,250,242,.96);
            border-radius: 999px;
            box-shadow: 0 10px 24px rgba(21,58,91,.22);
        }}

        .atlas-count {{
            background: var(--m4w-accent);
            color: #fffaf2;
            font-size: 1.35rem;
            font-weight: 850;
        }}

        .atlas-photo {{
            background-position: center;
            background-size: cover;
        }}

        .atlas-label {{
            position: absolute;
            top: calc(100% - .1rem);
            left: 50%;
            max-width: 9.5rem;
            transform: translateX(-50%);
            padding: .24rem .45rem;
            border: 1px solid rgba(196,168,130,.82);
            border-radius: 8px;
            background: rgba(255,250,242,.92);
            color: var(--m4w-text);
            font-size: .78rem;
            font-weight: 800;
            line-height: 1.15;
            text-align: center;
            white-space: normal;
        }}

        @media (max-width: 760px) {{
            .atlas-map {{
                min-height: 310px;
            }}
            .atlas-marker {{
                width: 3.6rem;
                height: 3.6rem;
            }}
            .atlas-count,
            .atlas-photo {{
                width: 3.05rem;
                height: 3.05rem;
            }}
            .atlas-label {{
                max-width: 7.2rem;
                font-size: .72rem;
            }}
        }}
        </style>
        <section class="atlas-map" aria-label="Mapa de lugares de la colección">
            <img class="atlas-world-map" src="{escape_html(world_map)}" alt="" aria-hidden="true">
            {"".join(markers)}
        </section>
        """
    )


def open_item(item_code: str) -> None:
    st.query_params.clear()
    switch_to_item(item_code)


def open_location(row: dict, selected_item_type: str | None) -> None:
    st.query_params.clear()
    switch_to_collection(
        country=row["target_value"] if row["target_kind"] == "country" else None,
        locality_ids=row["target_value"] if row["target_kind"] != "country" else None,
        zone=row["label"],
        item_type=selected_item_type,
    )


render_page_header(
    "Mapa",
    "Origen de la colección",
    "Explora tus minerales y colgantes por procedencia: las burbujas agrupan lugares con varias piezas y las fotos abren fichas individuales.",
    meta=["Mapa interactivo", "Burbujas por lugar", "Filtro por tipo"],
)

db = get_session()
try:
    opts = option_lists(db)

    render_section_heading(
        "Filtros del mapa",
        "Muestra solo el tipo de pieza, estado, mineral o país que quieres ver sobre el mapa.",
    )
    with st.container(border=True):
        type_col, sold_col, mineral_col, country_col = st.columns([1, 1, 1.4, 1.4])
        type_filter = type_col.selectbox("Tipo", opts["item_types"], index=opts["item_types"].index(ITEM_TYPE_FILTER_ALL))
        sold_filter = sold_col.selectbox("Estado", ["Todos", "Disponible", "Vendido"])
        mineral = mineral_col.selectbox("Mineral", opts["minerals"])
        country = country_col.selectbox("País", opts["countries"])

    sold = None
    if sold_filter == "Disponible":
        sold = False
    elif sold_filter == "Vendido":
        sold = True
    selected_item_type = item_type_from_filter(type_filter)

    items = list_collection_items(
        db,
        sold=sold,
        item_type=selected_item_type,
        mineral_name=mineral,
        country=country,
    )
    groups, missing_coordinates = group_items_by_location(items)
    single_rows, bubble_rows = build_marker_rows(groups)
    mapped_count = sum(len(group.items) for group in groups)

    render_metric_cards(
        [
            ("Lugares", len(groups), "Exactos o aproximados"),
            ("En mapa", mapped_count, "Piezas ubicadas"),
            ("Pendientes", missing_coordinates, "Sin ubicacion mapeable"),
        ]
    )

    if not groups:
        st.info("No hay piezas con origen mapeable para los filtros actuales. Anade pais, region conocida o latitud/longitud desde Alta / edicion.")
        st.stop()

    render_map(single_rows, bubble_rows, selected_item_type)

    all_rows = sorted(
        [*bubble_rows, *single_rows],
        key=lambda row: (-int(row["count"]), row["label"]),
    )
    render_section_heading(
        "Lugares del mapa",
        "Acceso directo por si prefieres abrir las zonas desde una lista.",
        aside=f"{len(all_rows)} lugar(es)",
    )
    for row in all_rows:
        label_col, meta_col, action_col = st.columns([2.2, 1.7, 1])
        label_col.markdown(f"**{row['label']}**")
        meta_col.caption(
            f"{row['count']} pieza(s) · {row['type_label']} · {row['minerals']} · {row['coordinate_note']}"
        )
        if row["target_kind"] == "item":
            if action_col.button("Abrir ficha", key=f"map_item_{row['target_value']}", use_container_width=True):
                open_item(row["target_value"])
        elif action_col.button("Ver zona", key=f"map_location_{row['target_value']}", use_container_width=True):
            open_location(row, selected_item_type)
finally:
    db.close()
