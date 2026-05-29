from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path
from statistics import median
from textwrap import dedent
from typing import Iterable

import streamlit as st
from PIL import Image, UnidentifiedImageError


def escape_html(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value).strip())


def mineral_initial(name: str | None) -> str:
    for character in str(name or "").strip():
        if character.isalnum():
            return character.upper()
    return "?"


def status_label(sold: bool) -> str:
    return "Vendido" if sold else "Disponible"


def status_class(sold: bool) -> str:
    return "is-sold" if sold else "is-available"


def render_html(markup: str) -> None:
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def render_global_styles() -> None:
    render_html(
        """
        <style>
        :root {
            --mineral-bg: #f5f2ea;
            --mineral-bg-soft: #ece7db;
            --mineral-panel: #ffffff;
            --mineral-panel-warm: #fbfaf6;
            --mineral-ink: #17211c;
            --mineral-soft-ink: #35443c;
            --mineral-muted: #66736c;
            --mineral-line: #ddd5c5;
            --mineral-line-strong: #c9bfaa;
            --mineral-forest: #284a3a;
            --mineral-forest-soft: #dfe8e0;
            --mineral-brass: #9c6a32;
            --mineral-brass-soft: #f0e0ca;
            --mineral-rust: #8a493e;
            --mineral-teal: #426b73;
            --mineral-shadow: 0 18px 45px rgba(23, 33, 28, .10);
            --mineral-shadow-soft: 0 10px 26px rgba(23, 33, 28, .08);
        }

        .stApp {
            background:
                radial-gradient(circle at 16% 0%, rgba(156, 106, 50, .09), transparent 31rem),
                linear-gradient(180deg, var(--mineral-bg) 0%, #faf8f2 46%, #f3efe6 100%);
            color: var(--mineral-ink);
        }

        .main .block-container {
            max-width: 1180px;
            padding-top: 2.25rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--mineral-ink);
        }

        p {
            color: var(--mineral-soft-ink);
        }

        [data-testid="stSidebar"] {
            background: rgba(244, 239, 228, .96);
            border-right: 1px solid var(--mineral-line);
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: .55rem;
        }

        [data-testid="stSidebarNav"] a {
            border-radius: 8px;
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, .76);
            border: 1px solid var(--mineral-line);
            border-radius: 8px;
            padding: .8rem .9rem;
            box-shadow: var(--mineral-shadow-soft);
        }

        [data-testid="stMetric"] label,
        [data-testid="stMetric"] [data-testid="stMetricLabel"] p {
            color: var(--mineral-muted);
        }

        div.stButton > button,
        div.stFormSubmitButton > button,
        div[data-testid="stLinkButton"] > a,
        .stDownloadButton > button {
            min-height: 2.5rem;
            border-radius: 8px;
            border: 1px solid var(--mineral-line-strong);
            color: var(--mineral-ink);
            background: rgba(255, 255, 255, .9);
            box-shadow: 0 2px 0 rgba(23, 33, 28, .04);
            transition: border-color .18s ease, color .18s ease, background .18s ease, transform .18s ease;
        }

        div.stButton > button p,
        div.stFormSubmitButton > button p,
        div[data-testid="stLinkButton"] > a p,
        .stDownloadButton > button p {
            color: inherit;
            font-weight: 650;
        }

        div.stButton > button:hover,
        div.stFormSubmitButton > button:hover,
        div[data-testid="stLinkButton"] > a:hover,
        .stDownloadButton > button:hover {
            border-color: var(--mineral-forest);
            color: var(--mineral-forest);
            background: #ffffff;
            transform: translateY(-1px);
        }

        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primaryFormSubmit"],
        button[data-testid="stBaseButton-primaryFormSubmit"],
        div.stButton > button[data-testid="baseButton-primary"] {
            background: var(--mineral-forest);
            border-color: var(--mineral-forest);
            color: #ffffff;
        }

        div.stButton > button[kind="primary"] p,
        div.stFormSubmitButton > button[kind="primary"] p,
        div.stFormSubmitButton > button[kind="primaryFormSubmit"] p,
        button[data-testid="stBaseButton-primaryFormSubmit"] p,
        div.stButton > button[data-testid="baseButton-primary"] p {
            color: #ffffff;
        }

        div.stButton > button[kind="primary"]:hover,
        div.stFormSubmitButton > button[kind="primary"]:hover,
        div.stFormSubmitButton > button[kind="primaryFormSubmit"]:hover,
        button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
        div.stButton > button[data-testid="baseButton-primary"]:hover {
            background: #1f3c2f;
            color: #ffffff;
        }

        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] {
            border-radius: 8px;
        }

        [data-testid="stFileUploader"] section {
            border-radius: 8px;
            border-color: var(--mineral-line);
            background: rgba(255, 255, 255, .72);
        }

        .stTabs [data-baseweb="tab"] p {
            color: var(--mineral-muted);
            font-weight: 650;
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] p {
            color: var(--mineral-forest);
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--mineral-forest);
        }

        .premium-hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(23, 33, 28, .11);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, .94), rgba(251, 250, 246, .82)),
                linear-gradient(125deg, rgba(40, 74, 58, .16), rgba(156, 106, 50, .12));
            box-shadow: var(--mineral-shadow);
            padding: clamp(1.25rem, 4vw, 2.4rem);
            margin-bottom: 1.15rem;
        }

        .premium-hero::after {
            content: "";
            position: absolute;
            right: -4rem;
            top: -6rem;
            width: 18rem;
            height: 18rem;
            border: 1px solid rgba(40, 74, 58, .14);
            transform: rotate(24deg);
        }

        .premium-hero > * {
            position: relative;
            z-index: 1;
        }

        .hero-kicker,
        .section-kicker {
            color: var(--mineral-brass);
            font-size: .74rem;
            font-weight: 750;
            letter-spacing: .08em;
            margin: 0 0 .45rem;
            text-transform: uppercase;
        }

        .hero-title,
        .section-title {
            color: var(--mineral-ink);
            font-weight: 780;
        }

        .hero-title {
            font-size: clamp(2.1rem, 5vw, 4.1rem);
            line-height: .96;
            margin: 0;
            max-width: 12ch;
        }

        .hero-copy {
            color: var(--mineral-muted);
            font-size: clamp(1rem, 2vw, 1.15rem);
            line-height: 1.55;
            max-width: 58rem;
            margin: .85rem 0 0;
        }

        .hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: 1.15rem;
        }

        .premium-chip,
        .status-chip {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            min-height: 1.8rem;
            padding: .22rem .58rem;
            border-radius: 999px;
            border: 1px solid rgba(23, 33, 28, .12);
            background: rgba(255, 255, 255, .72);
            color: var(--mineral-soft-ink);
            font-size: .8rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .status-chip.is-available {
            border-color: rgba(40, 74, 58, .23);
            background: var(--mineral-forest-soft);
            color: var(--mineral-forest);
        }

        .status-chip.is-sold {
            border-color: rgba(138, 73, 62, .24);
            background: #f4ded8;
            color: var(--mineral-rust);
        }

        .metric-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: .75rem;
            margin: 1rem 0 1.4rem;
        }

        .metric-card,
        .detail-card,
        .info-panel,
        .filter-shell {
            border: 1px solid rgba(23, 33, 28, .11);
            border-radius: 8px;
            background: rgba(255, 255, 255, .82);
            box-shadow: var(--mineral-shadow-soft);
        }

        .metric-card {
            padding: .85rem .95rem;
        }

        .metric-label {
            color: var(--mineral-muted);
            font-size: .78rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: .05em;
            margin: 0 0 .25rem;
        }

        .metric-value {
            color: var(--mineral-ink);
            font-size: 1.85rem;
            line-height: 1;
            font-weight: 780;
            margin: 0;
        }

        .metric-note {
            color: var(--mineral-muted);
            font-size: .86rem;
            margin: .35rem 0 0;
        }

        .section-heading {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin: 1.45rem 0 .65rem;
        }

        .section-title {
            font-size: 2rem;
            line-height: 1.15;
            margin: 0;
        }

        .section-heading p {
            color: var(--mineral-muted);
            margin: .22rem 0 0;
        }

        .filter-shell {
            padding: .95rem;
            margin: .8rem 0 1rem;
        }

        .filter-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .75rem;
            color: var(--mineral-muted);
            font-size: .78rem;
            font-weight: 750;
            letter-spacing: .05em;
            text-transform: uppercase;
            margin-bottom: .4rem;
        }

        .collection-card {
            overflow: hidden;
            border: 1px solid rgba(23, 33, 28, .12);
            border-radius: 8px;
            background: rgba(255, 255, 255, .86);
            box-shadow: var(--mineral-shadow-soft);
            margin-bottom: .55rem;
        }

        .collection-visual {
            position: relative;
            aspect-ratio: 1 / 1.08;
            overflow: hidden;
            background:
                linear-gradient(135deg, rgba(40, 74, 58, .16), rgba(156, 106, 50, .15)),
                #e5dfd1;
        }

        .collection-visual img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform .24s ease, filter .24s ease;
        }

        .collection-card:hover .collection-visual img {
            transform: scale(1.04);
            filter: saturate(1.06) contrast(1.03);
        }

        .collection-placeholder,
        .native-photo-placeholder,
        .premium-photo-placeholder {
            display: grid;
            place-items: center;
            width: 100%;
            height: 100%;
            background:
                linear-gradient(145deg, rgba(40, 74, 58, .16), rgba(66, 107, 115, .13) 48%, rgba(156, 106, 50, .17)),
                #e8e1d3;
            color: var(--mineral-forest);
        }

        .collection-placeholder-inner,
        .premium-photo-placeholder-inner {
            display: grid;
            gap: .25rem;
            place-items: center;
            padding: 1rem;
            text-align: center;
        }

        .collection-placeholder-initial,
        .premium-photo-placeholder-initial,
        .native-photo-placeholder span {
            display: grid;
            place-items: center;
            width: 4.2rem;
            height: 4.2rem;
            border: 1px solid rgba(40, 74, 58, .20);
            border-radius: 999px;
            background: rgba(255, 255, 255, .62);
            color: var(--mineral-forest);
            font-size: 2.2rem;
            font-weight: 780;
            line-height: 1;
        }

        .collection-placeholder-label,
        .premium-photo-placeholder-label {
            color: var(--mineral-muted);
            font-size: .82rem;
            font-weight: 700;
        }

        .collection-status {
            position: absolute;
            top: .65rem;
            left: .65rem;
        }

        .collection-body {
            padding: .8rem .85rem .9rem;
        }

        .collection-title {
            color: var(--mineral-ink);
            font-size: 1rem;
            font-weight: 760;
            line-height: 1.2;
            margin: 0;
        }

        .collection-meta {
            color: var(--mineral-muted);
            font-size: .84rem;
            line-height: 1.35;
            margin: .35rem 0 0;
        }

        .collection-code {
            color: var(--mineral-brass);
            font-size: .76rem;
            font-weight: 760;
            letter-spacing: .04em;
            text-transform: uppercase;
            margin-bottom: .28rem;
        }

        .native-photo-placeholder,
        .premium-photo-placeholder {
            aspect-ratio: 1 / var(--photo-frame-ratio, 1);
            border: 1px solid rgba(23, 33, 28, .12);
            border-radius: 8px;
            min-height: 13rem;
        }

        .stable-photo-frame {
            width: 100%;
            margin: 0;
        }

        .stable-photo-stage {
            width: 100%;
            aspect-ratio: 1 / var(--photo-frame-ratio, 1);
            display: grid;
            place-items: center;
            overflow: hidden;
            border-radius: 8px;
            border: 1px solid rgba(23, 33, 28, .12);
            background:
                linear-gradient(145deg, rgba(255, 255, 255, .82), rgba(245, 242, 234, .82)),
                #ffffff;
            box-shadow: var(--mineral-shadow-soft);
        }

        .stable-photo-stage img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .stable-photo-caption {
            margin-top: .45rem;
            color: var(--mineral-muted);
            font-size: .84rem;
            line-height: 1.35;
        }

        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: .7rem;
            margin: .75rem 0 1rem;
        }

        .detail-card {
            padding: .78rem .86rem;
        }

        .detail-label {
            color: var(--mineral-muted);
            font-size: .72rem;
            font-weight: 760;
            letter-spacing: .05em;
            text-transform: uppercase;
            margin: 0 0 .25rem;
        }

        .detail-value {
            color: var(--mineral-ink);
            font-size: .96rem;
            line-height: 1.42;
            margin: 0;
        }

        .info-panel {
            padding: 1rem;
            margin: .75rem 0;
        }

        .info-panel h3,
        .info-panel h4 {
            margin-top: 0;
        }

        .wiki-photo {
            overflow: hidden;
            border: 1px solid rgba(23, 33, 28, .12);
            border-radius: 8px;
            background: rgba(255, 255, 255, .82);
            box-shadow: var(--mineral-shadow-soft);
        }

        .wiki-photo-media {
            width: 100%;
            min-height: 14rem;
            background:
                linear-gradient(145deg, rgba(40, 74, 58, .16), rgba(66, 107, 115, .13) 48%, rgba(156, 106, 50, .17)),
                var(--wiki-photo-url),
                #e8e1d3;
            background-position: center;
            background-size: cover;
        }

        .wiki-photo-body {
            padding: .72rem .78rem .85rem;
        }

        .wiki-photo-caption {
            color: var(--mineral-muted);
            font-size: .84rem;
            line-height: 1.35;
            margin: 0;
        }

        .admin-corner {
            position: fixed;
            left: .8rem;
            bottom: .8rem;
            z-index: 1000;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: .25rem .48rem;
            border-radius: 6px;
            color: rgba(23, 33, 28, .58);
            background: rgba(245, 242, 234, .86);
            border: 1px solid rgba(23, 33, 28, .12);
            font-size: .72rem;
            line-height: 1;
            text-decoration: none;
        }

        .admin-corner:hover {
            color: var(--mineral-forest);
            border-color: rgba(40, 74, 58, .38);
        }

        @media (max-width: 760px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .premium-hero {
                padding: 1.15rem;
            }

            .hero-title {
                max-width: 100%;
            }

            .section-heading {
                display: block;
            }

            .admin-corner {
                left: auto;
                right: .5rem;
                bottom: .5rem;
            }
        }
        </style>
        """
    )


def render_page_header(
    kicker: str,
    title: str,
    subtitle: str,
    meta: Iterable[str] | None = None,
) -> None:
    meta_html = ""
    if meta:
        chips = "".join(f'<span class="premium-chip">{escape_html(item)}</span>' for item in meta if item)
        if chips:
            meta_html = f'<div class="hero-meta">{chips}</div>'

    render_html(
        f"""
        <section class="premium-hero">
            <p class="hero-kicker">{escape_html(kicker)}</p>
            <div class="hero-title" role="heading" aria-level="1">{escape_html(title)}</div>
            <p class="hero-copy">{escape_html(subtitle)}</p>
            {meta_html}
        </section>
        """
    )


def render_section_heading(title: str, subtitle: str | None = None, aside: str | None = None) -> None:
    subtitle_html = f"<p>{escape_html(subtitle)}</p>" if subtitle else ""
    aside_html = f'<span class="premium-chip">{escape_html(aside)}</span>' if aside else ""
    render_html(
        f"""
        <div class="section-heading">
            <div>
                <p class="section-kicker">Catálogo</p>
                <div class="section-title" role="heading" aria-level="2">{escape_html(title)}</div>
                {subtitle_html}
            </div>
            {aside_html}
        </div>
        """
    )


def render_metric_cards(metrics: Iterable[tuple[str, object, str | None]]) -> None:
    cards = []
    for label, value, note in metrics:
        note_html = f'<p class="metric-note">{escape_html(note)}</p>' if note else ""
        cards.append(
            '<article class="metric-card">'
            f'<p class="metric-label">{escape_html(label)}</p>'
            f'<p class="metric-value">{escape_html(value)}</p>'
            f"{note_html}"
            "</article>"
        )

    render_html(f'<div class="metric-strip">{"".join(cards)}</div>')


def render_filter_shell(label: str, count_label: str) -> None:
    render_html(
        f"""
        <div class="filter-shell">
            <div class="filter-title">
                <span>{escape_html(label)}</span>
                <span>{escape_html(count_label)}</span>
            </div>
        </div>
        """
    )


def render_detail_grid(rows: Iterable[tuple[str, object]], empty_message: str | None = None) -> bool:
    cards = []
    for label, value in rows:
        clean_value = str(value or "").strip()
        if not clean_value:
            continue
        cards.append(
            '<article class="detail-card">'
            f'<p class="detail-label">{escape_html(label)}</p>'
            f'<p class="detail-value">{escape_html(clean_value)}</p>'
            "</article>"
        )

    if not cards:
        if empty_message:
            st.info(empty_message)
        return False

    render_html(f'<div class="detail-grid">{"".join(cards)}</div>')
    return True


def render_status_chip(sold: bool) -> str:
    return f'<span class="status-chip {status_class(sold)}">{status_label(sold)}</span>'


def _placeholder_markup(title: str, subtitle: str | None = None) -> str:
    subtitle_html = (
        f'<span class="premium-photo-placeholder-label">{escape_html(subtitle)}</span>'
        if subtitle
        else ""
    )
    return (
        '<div class="premium-photo-placeholder">'
        '<div class="premium-photo-placeholder-inner">'
        f'<span class="premium-photo-placeholder-initial">{escape_html(mineral_initial(title))}</span>'
        f"{subtitle_html}"
        "</div>"
        "</div>"
    )


def render_photo_placeholder(title: str, subtitle: str | None = None, frame_ratio: float = 1.0) -> None:
    render_html(
        f'<div style="--photo-frame-ratio: {frame_ratio:.6f};">{_placeholder_markup(title, subtitle)}</div>',
    )


def render_collection_card(
    *,
    item_code: str,
    title: str,
    mineral_name: str,
    country: str | None,
    sold: bool,
    cover_path: Path | None,
) -> None:
    image_html = ""
    if cover_path and cover_path.exists():
        data_uri = _image_data_uri(str(cover_path), cover_path.stat().st_mtime_ns)
        if data_uri:
            image_html = f'<img src="{data_uri}" alt="{escape_html(title)}">'

    if not image_html:
        image_html = (
            '<div class="collection-placeholder">'
            '<div class="collection-placeholder-inner">'
            f'<span class="collection-placeholder-initial">{escape_html(mineral_initial(mineral_name))}</span>'
            '<span class="collection-placeholder-label">Foto pendiente</span>'
            "</div>"
            "</div>"
        )

    locality = country or "Localidad por completar"
    render_html(
        f"""
        <article class="collection-card">
            <div class="collection-visual">
                {image_html}
                <div class="collection-status">{render_status_chip(sold)}</div>
            </div>
            <div class="collection-body">
                <div class="collection-code">{escape_html(item_code)}</div>
                <h3 class="collection-title">{escape_html(title)}</h3>
                <p class="collection-meta">{escape_html(mineral_name)} · {escape_html(locality)}</p>
            </div>
        </article>
        """
    )


def image_height_ratio(path: Path) -> float | None:
    try:
        with Image.open(path) as image:
            width, height = image.size
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return None

    if width <= 0 or height <= 0:
        return None
    return height / width


def max_image_height_ratio(paths: list[Path], default: float = 1.0) -> float:
    ratios = [ratio for path in paths if (ratio := image_height_ratio(path))]
    return max(ratios, default=default)


def shared_image_frame_ratio(
    paths: list[Path],
    default: float = 1.0,
    min_ratio: float = 0.75,
    max_ratio: float = 1.35,
) -> float:
    ratios = [ratio for path in paths if (ratio := image_height_ratio(path))]
    if not ratios:
        return default

    baseline = float(median(ratios))
    return min(max(baseline, min_ratio), max_ratio)


@st.cache_data(show_spinner=False)
def _image_data_uri(path_text: str, mtime_ns: int) -> str | None:
    path = Path(path_text)
    if not path.exists():
        return None

    mime_type = mimetypes.guess_type(path.name)[0] or "image/webp"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_stable_photo(path: Path, frame_ratio: float, caption: str | None = None) -> None:
    if not path.exists():
        st.warning("Archivo no encontrado.")
        return

    data_uri = _image_data_uri(str(path), path.stat().st_mtime_ns)
    if not data_uri:
        st.warning("Archivo no encontrado.")
        return

    caption_html = ""
    if caption:
        caption_html = f'<figcaption class="stable-photo-caption">{escape_html(caption)}</figcaption>'

    render_html(
        f"""
        <figure class="stable-photo-frame" style="--photo-frame-ratio: {frame_ratio:.6f};">
            <div class="stable-photo-stage">
                <img src="{data_uri}" alt="{escape_html(caption or path.name)}">
            </div>
            {caption_html}
        </figure>
        """
    )
