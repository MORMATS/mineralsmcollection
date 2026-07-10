from __future__ import annotations

import base64
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps, UnidentifiedImageError

from src.crud import list_collection_map_items, option_lists
from src.db import DATA_DIR, UPLOAD_DIR, get_session
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


MAP_THUMBNAIL_DIR = DATA_DIR / "map_thumbnails"
MAP_THUMBNAIL_SIZE = (112, 112)
MAP_THUMBNAIL_QUALITY = 72
MAP_MAX_SLIDES_PER_MARKER = 5


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


def map_thumbnail_cache_path(path: Path, mtime_ns: int) -> Path:
    digest = hashlib.sha1(
        f"{path.resolve()}:{mtime_ns}:{MAP_THUMBNAIL_SIZE[0]}x{MAP_THUMBNAIL_SIZE[1]}".encode("utf-8")
    ).hexdigest()
    return MAP_THUMBNAIL_DIR / f"{digest}.jpg"


def save_map_thumbnail(source_path: Path, cache_path: Path) -> bool:
    try:
        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image)
            if "A" in image.getbands():
                background = Image.new("RGB", image.size, (255, 250, 242))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS

            thumbnail = ImageOps.fit(image, MAP_THUMBNAIL_SIZE, method=resample)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            thumbnail.save(cache_path, format="JPEG", quality=MAP_THUMBNAIL_QUALITY, optimize=True)
            return True
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return False


@st.cache_data(show_spinner=False)
def map_thumbnail_data_uri(path_text: str, mtime_ns: int) -> str | None:
    path = Path(path_text)
    if not path.exists():
        return None

    cache_path = map_thumbnail_cache_path(path, mtime_ns)
    if not cache_path.exists() and not save_map_thumbnail(path, cache_path):
        return None

    encoded = base64.b64encode(cache_path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def map_photo_slides(items: list, limit: int = MAP_MAX_SLIDES_PER_MARKER) -> list[str]:
    slides = []
    for item in items:
        cover_path = cover_image_path(item)
        if not cover_path:
            continue

        data_uri = map_thumbnail_data_uri(str(cover_path), cover_path.stat().st_mtime_ns)
        if data_uri:
            slides.append(data_uri)
        if len(slides) >= limit:
            break

    return slides


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
            "photo_slides": map_photo_slides(items),
        }

        if count == 1:
            base_row.update(
                {
                    "target_kind": "item",
                    "target_value": first_item.item_code,
                    "action": "Abrir ficha",
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
    return "?" + urlencode(params)


def short_map_label(label: str, limit: int = 30) -> str:
    clean = str(label or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "..."


def script_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True).replace("</", "<\\/")


def leaflet_marker_payload(row: dict, selected_item_type: str | None) -> dict:
    return {
        "lat": float(row["latitude"]),
        "lon": float(row["longitude"]),
        "label": row["label"],
        "shortLabel": short_map_label(row["label"]),
        "count": int(row["count"]),
        "countText": str(row["count_text"]),
        "typeLabel": row["type_label"],
        "minerals": row["minerals"],
        "itemCodes": row["item_codes"],
        "note": row["coordinate_note"],
        "href": map_marker_href(row, selected_item_type),
        "action": row["action"],
        "kind": row["target_kind"],
        "slides": row["photo_slides"],
    }


def render_map(single_rows: list[dict], bubble_rows: list[dict], selected_item_type: str | None) -> None:
    rows = [*bubble_rows, *single_rows]
    map_rows_json = script_json([leaflet_marker_payload(row, selected_item_type) for row in rows])
    map_html = """
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="preconnect" href="https://unpkg.com" crossorigin>
        <link rel="preconnect" href="https://tile.openstreetmap.org" crossorigin>
        <link rel="dns-prefetch" href="//unpkg.com">
        <link rel="dns-prefetch" href="//tile.openstreetmap.org">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
        <style>
        :root {
            --m4w-accent: #153a5b;
            --m4w-accent-2: #1e5080;
            --m4w-border: #c4a882;
            --m4w-surface: #fffaf2;
            --m4w-surface-muted: #ede8de;
            --m4w-text: #3c2f2f;
            --m4w-text-light: #6b4e2e;
            --marker-scale: 1;
            --label-size: 12px;
        }

        html,
        body {
            width: 100%;
            height: 100%;
            margin: 0;
            background: transparent;
            color: var(--m4w-text);
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            letter-spacing: 0;
            overflow: hidden;
        }

        .map-shell {
            position: relative;
            width: 100%;
            height: 610px;
            overflow: hidden;
            border: 1px solid var(--m4w-border);
            border-radius: 8px;
            background: #dbe8ee;
            box-sizing: border-box;
        }

        #collection-map {
            width: 100%;
            height: 100%;
            background: #dbe8ee;
        }

        .map-fallback {
            position: absolute;
            inset: 0;
            z-index: 600;
            display: grid;
            place-items: center;
            padding: 1rem;
            background: rgba(255, 250, 242, .92);
            color: var(--m4w-text-light);
            font-size: .92rem;
            font-weight: 750;
            text-align: center;
        }

        .map-fallback.is-hidden {
            display: none;
        }

        .leaflet-container {
            font: inherit;
        }

        .leaflet-control-attribution {
            color: #334;
            font-size: 10px;
        }

        .leaflet-control-attribution a {
            color: var(--m4w-accent);
        }

        .atlas-div-icon {
            background: transparent;
            border: 0;
        }

        .atlas-pin {
            position: relative;
            display: grid;
            place-items: center;
            width: calc(42px * var(--marker-scale));
            height: calc(42px * var(--marker-scale));
            border: 4px solid rgba(255, 250, 242, .96);
            border-radius: 999px;
            background: var(--m4w-accent);
            box-shadow: 0 10px 24px rgba(21, 58, 91, .24);
            color: #fffaf2;
            font-size: calc(16px * var(--marker-scale));
            font-weight: 850;
            line-height: 1;
            transform: translate(-50%, -50%);
            transition: transform .16s ease, filter .16s ease, width .16s ease, height .16s ease;
        }

        .atlas-pin.has-photo {
            width: calc(56px * var(--marker-scale));
            height: calc(56px * var(--marker-scale));
            overflow: hidden;
            background: #0f2c45;
            isolation: isolate;
        }

        .atlas-pin:hover {
            transform: translate(-50%, -50%) scale(1.08);
            filter: saturate(1.08) contrast(1.04);
        }

        .atlas-pin.is-item {
            background: var(--m4w-accent-2);
        }

        .atlas-pin.is-bubble {
            background: var(--m4w-accent);
        }

        .atlas-slide {
            position: absolute;
            inset: 0;
            z-index: 0;
            background-position: center;
            background-size: cover;
            opacity: 0;
        }

        .atlas-pin.has-photo:not(.is-slideshow) .atlas-slide {
            opacity: 1;
        }

        .atlas-pin.is-slideshow .atlas-slide {
            animation-name: atlas-slide-fade;
            animation-timing-function: ease-in-out;
            animation-iteration-count: infinite;
        }

        .atlas-pin.has-photo::after {
            content: "";
            position: absolute;
            inset: 0;
            z-index: 1;
            border-radius: inherit;
            box-shadow:
                inset 0 0 0 1px rgba(21, 58, 91, .24),
                inset 0 -18px 28px rgba(15, 44, 69, .25);
            pointer-events: none;
        }

        .atlas-photo-count {
            position: absolute;
            right: -.25rem;
            bottom: -.25rem;
            z-index: 2;
            display: grid;
            place-items: center;
            min-width: 1.45rem;
            height: 1.45rem;
            padding: 0 .22rem;
            border: 2px solid rgba(255, 250, 242, .96);
            border-radius: 999px;
            background: var(--m4w-accent);
            color: #fffaf2;
            box-shadow: 0 6px 14px rgba(21, 58, 91, .22);
            font-size: .72rem;
            font-weight: 850;
            line-height: 1;
        }

        @keyframes atlas-slide-fade {
            0%, 30% {
                opacity: 1;
            }
            38%, 100% {
                opacity: 0;
            }
        }

        .atlas-map-label {
            max-width: 180px;
            overflow: hidden;
            border: 1px solid rgba(196, 168, 130, .82);
            border-radius: 8px;
            background: rgba(255, 250, 242, .94);
            color: var(--m4w-text);
            box-shadow: 0 5px 14px rgba(21, 58, 91, .14);
            font-size: var(--label-size);
            font-weight: 800;
            line-height: 1.15;
            text-align: center;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .atlas-map-label::before {
            display: none;
        }

        .atlas-popup {
            min-width: 210px;
            max-width: 260px;
        }

        .atlas-popup-title {
            margin: 0 0 .25rem;
            color: var(--m4w-accent);
            font-size: .98rem;
            font-weight: 850;
            line-height: 1.18;
        }

        .atlas-popup-meta,
        .atlas-popup-note {
            margin: .24rem 0 0;
            color: var(--m4w-text-light);
            font-size: .8rem;
            font-weight: 650;
            line-height: 1.3;
        }

        .atlas-popup-action {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 34px;
            margin-top: .7rem;
            padding: .25rem .68rem;
            border: 1px solid var(--m4w-accent);
            border-radius: 8px;
            background: var(--m4w-accent);
            color: #fffaf2 !important;
            font-size: .82rem;
            font-weight: 800;
            line-height: 1.1;
            text-decoration: none;
        }

        .atlas-popup-action:hover {
            background: #0f2c45;
            border-color: #0f2c45;
        }

        @media (max-width: 760px) {
            .atlas-map-label {
                max-width: 130px;
            }
        }
        </style>
    </head>
    <body>
        <div class="map-shell">
            <div id="collection-map" aria-label="Mapa real de lugares de la coleccion"></div>
            <div id="map-fallback" class="map-fallback">Cargando mapa real...</div>
        </div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        (() => {
            const rows = __MAP_ROWS__;
            const shell = document.querySelector(".map-shell");
            const fallback = document.getElementById("map-fallback");

            const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[character]));

            const clamp = (value, minimum, maximum) => Math.min(Math.max(value, minimum), maximum);

            const showFallback = (message) => {
                fallback.textContent = message;
                fallback.classList.remove("is-hidden");
            };

            const hideFallback = () => fallback.classList.add("is-hidden");

            const navigateInsideApp = (href) => {
                const target = new URL(href, window.parent.location.href);
                try {
                    window.parent.history.pushState({ source: "collection-map" }, "", target.href);
                    window.parent.location.reload();
                    return true;
                } catch (error) {
                    return false;
                }
            };

            document.addEventListener("click", (event) => {
                const action = event.target.closest("[data-map-href]");
                if (!action) {
                    return;
                }

                const href = action.getAttribute("data-map-href") || action.getAttribute("href");
                if (href && navigateInsideApp(href)) {
                    event.preventDefault();
                    event.stopPropagation();
                }
            });

            const markerHtml = (row) => {
                const markerClass = row.kind === "item" ? "is-item" : "is-bubble";
                const slides = Array.isArray(row.slides) ? row.slides.filter(Boolean) : [];
                if (slides.length) {
                    const duration = Math.max(8, slides.length * 3.25);
                    const step = duration / slides.length;
                    const slideHtml = slides.map((slide, index) => (
                        `<span class="atlas-slide" style="background-image:url('${escapeHtml(slide)}'); animation-duration:${duration.toFixed(2)}s; animation-delay:${(-index * step).toFixed(2)}s"></span>`
                    )).join("");
                    const slideshowClass = slides.length > 1 ? "is-slideshow" : "";
                    const countBadge = row.count > 1 ? `<span class="atlas-photo-count">${escapeHtml(row.countText)}</span>` : "";
                    return `<span class="atlas-pin ${markerClass} has-photo ${slideshowClass}" aria-hidden="true">${slideHtml}${countBadge}</span>`;
                }

                const markerText = row.kind === "item" ? "1" : row.countText;
                return `<span class="atlas-pin ${markerClass}" aria-hidden="true">${escapeHtml(markerText)}</span>`;
            };

            const popupHtml = (row) => `
                <article class="atlas-popup">
                    <h3 class="atlas-popup-title">${escapeHtml(row.label)}</h3>
                    <p class="atlas-popup-meta">${escapeHtml(row.count)} pieza(s) &middot; ${escapeHtml(row.typeLabel)}</p>
                    <p class="atlas-popup-meta">${escapeHtml(row.minerals)}</p>
                    <p class="atlas-popup-note">${escapeHtml(row.note)}</p>
                    <a class="atlas-popup-action" href="${escapeHtml(row.href)}" data-map-href="${escapeHtml(row.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(row.action)}</a>
                </article>
            `;

            const initMap = () => {
                if (!window.L) {
                    showFallback("No se pudo cargar Leaflet. Revisa la conexion del navegador o el CDN.");
                    return;
                }
                if (!rows.length) {
                    showFallback("No hay ubicaciones mapeables para mostrar.");
                    return;
                }

                const map = L.map("collection-map", {
                    center: [20, 0],
                    zoom: 2,
                    minZoom: 2,
                    maxZoom: 18,
                    preferCanvas: true,
                    worldCopyJump: true,
                    scrollWheelZoom: true,
                    fadeAnimation: false,
                    markerZoomAnimation: false,
                    zoomControl: true
                });

                L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    maxZoom: 19,
                    detectRetina: false,
                    keepBuffer: 2,
                    updateWhenIdle: true,
                    updateWhenZooming: false,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
                }).addTo(map);

                const markerEntries = [];
                const bounds = [];

                rows.forEach((row) => {
                    const marker = L.marker([row.lat, row.lon], {
                        icon: L.divIcon({
                            className: "atlas-div-icon",
                            html: markerHtml(row),
                            iconSize: [1, 1],
                            iconAnchor: [0, 0]
                        }),
                        title: row.label
                    }).addTo(map);

                    marker.bindPopup(popupHtml(row), {
                        closeButton: true,
                        maxWidth: 280
                    });

                    markerEntries.push({ marker, row });
                    bounds.push([row.lat, row.lon]);
                });

                if (bounds.length > 1) {
                    map.fitBounds(bounds, {
                        padding: [42, 42],
                        maxZoom: 6
                    });
                } else {
                    map.setView(bounds[0], 5);
                }

                const labelZoom = rows.length > 35 ? 8 : rows.length > 14 ? 7 : 6;

                const updateDensity = () => {
                    const zoom = map.getZoom();
                    const scale = clamp(.72 + zoom * .055, .84, 1.24);
                    const labelSize = clamp(9.5 + zoom * .34, 10, 13);
                    shell.style.setProperty("--marker-scale", scale.toFixed(2));
                    shell.style.setProperty("--label-size", `${labelSize.toFixed(1)}px`);

                    markerEntries.forEach(({ marker, row }) => {
                        const existingTooltip = marker.getTooltip();
                        if (zoom < labelZoom) {
                            if (existingTooltip) {
                                marker.unbindTooltip();
                            }
                            return;
                        }

                        const label = zoom >= labelZoom + 2 ? row.label : row.shortLabel;
                        if (existingTooltip) {
                            marker.setTooltipContent(escapeHtml(label));
                        } else {
                            marker.bindTooltip(escapeHtml(label), {
                                className: "atlas-map-label",
                                direction: "top",
                                offset: [0, -24],
                                opacity: 1,
                                permanent: true
                            });
                        }
                    });
                };

                map.on("zoomend", updateDensity);
                map.on("moveend", updateDensity);
                setTimeout(() => {
                    map.invalidateSize();
                    updateDensity();
                    hideFallback();
                }, 100);
            };

            if (document.readyState === "loading") {
                document.addEventListener("DOMContentLoaded", initMap);
            } else {
                initMap();
            }
        })();
        </script>
    </body>
    </html>
    """.replace("__MAP_ROWS__", map_rows_json)

    components.html(map_html, height=622, scrolling=False)


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

    items = list_collection_map_items(
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
