from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path
from statistics import median

import streamlit as st
from PIL import Image, UnidentifiedImageError


def render_global_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --mineral-bg: #f7f5ef;
            --mineral-panel: #ffffff;
            --mineral-ink: #23302a;
            --mineral-muted: #66736c;
            --mineral-line: #ded9cb;
            --mineral-green: #496b5a;
            --mineral-amber: #9a6d35;
            --mineral-blue: #4f6f86;
        }

        .stApp {
            background: var(--mineral-bg);
            color: var(--mineral-ink);
        }

        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--mineral-ink);
        }

        [data-testid="stSidebar"] {
            background: #efebe0;
            border-right: 1px solid var(--mineral-line);
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: .45rem;
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, .72);
            border: 1px solid var(--mineral-line);
            border-radius: 8px;
            padding: .8rem .9rem;
        }

        div.stButton > button,
        div[data-testid="stLinkButton"] > a {
            border-radius: 8px;
            border-color: #cfc7b7;
            color: var(--mineral-ink);
            background: rgba(255, 255, 255, .84);
        }

        div.stButton > button p,
        div[data-testid="stLinkButton"] > a p {
            color: var(--mineral-ink);
        }

        div.stButton > button:hover,
        div[data-testid="stLinkButton"] > a:hover {
            border-color: var(--mineral-green);
            color: var(--mineral-green);
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] p {
            color: var(--mineral-green);
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--mineral-green);
        }

        .collection-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
            gap: 16px;
            margin-top: 1rem;
        }

        .collection-card {
            position: relative;
            display: block;
            aspect-ratio: 1 / 1.18;
            overflow: hidden;
            border-radius: 8px;
            border: 1px solid rgba(35, 48, 42, .13);
            background: #e7e1d3;
            box-shadow: 0 12px 30px rgba(35, 48, 42, .08);
            text-decoration: none;
            color: white;
        }

        .collection-card * {
            text-decoration: none;
        }

        .collection-photo,
        .collection-photo img,
        .collection-placeholder {
            display: block;
            width: 100%;
            height: 100%;
        }

        .collection-photo img {
            object-fit: cover;
            transition: transform .24s ease, filter .24s ease;
        }

        .collection-placeholder {
            display: grid;
            place-items: center;
            background:
                linear-gradient(135deg, rgba(73, 107, 90, .18), rgba(154, 109, 53, .16)),
                #ded8c8;
            color: var(--mineral-green);
            font-size: 4rem;
            font-weight: 700;
        }

        .collection-placeholder span {
            color: var(--mineral-green);
        }

        .collection-overlay {
            position: absolute;
            inset: auto 0 0 0;
            padding: .85rem;
            background: linear-gradient(to top, rgba(19, 24, 21, .78), rgba(19, 24, 21, .08));
            display: flex;
            flex-direction: column;
            gap: .08rem;
        }

        .collection-card:hover img {
            transform: scale(1.04);
            filter: saturate(1.05);
        }

        .collection-badge {
            align-self: flex-start;
            margin-bottom: .25rem;
            padding: .16rem .42rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, .88);
            color: var(--mineral-ink);
            font-size: .72rem;
            font-weight: 700;
        }

        .collection-title {
            font-size: .98rem;
            font-weight: 700;
            line-height: 1.15;
            color: white;
        }

        .collection-meta {
            font-size: .78rem;
            line-height: 1.2;
            color: rgba(255, 255, 255, .82);
        }

        .native-photo-placeholder {
            width: 100%;
            aspect-ratio: 1 / var(--photo-frame-ratio, 1);
            display: grid;
            place-items: center;
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(73, 107, 90, .18), rgba(154, 109, 53, .16)),
                #ded8c8;
            color: var(--mineral-green);
            font-size: 4rem;
            font-weight: 700;
        }

        .native-photo-placeholder span {
            color: var(--mineral-green);
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
            border: 1px solid rgba(35, 48, 42, .12);
            background: rgba(255, 255, 255, .66);
        }

        .stable-photo-stage img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .stable-photo-caption {
            margin-top: .35rem;
            color: var(--mineral-muted);
            font-size: .82rem;
            line-height: 1.3;
        }

        .admin-corner {
            position: fixed;
            left: .8rem;
            bottom: .8rem;
            z-index: 1000;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: .22rem .45rem;
            border-radius: 6px;
            color: rgba(35, 48, 42, .56);
            background: rgba(247, 245, 239, .82);
            border: 1px solid rgba(35, 48, 42, .12);
            font-size: .72rem;
            line-height: 1;
            text-decoration: none;
        }

        .admin-corner:hover {
            color: var(--mineral-green);
            border-color: rgba(73, 107, 90, .42);
        }
        </style>
        """,
        unsafe_allow_html=True,
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
        caption_html = f'<figcaption class="stable-photo-caption">{html.escape(caption)}</figcaption>'

    st.markdown(
        f"""
        <figure class="stable-photo-frame" style="--photo-frame-ratio: {frame_ratio:.6f};">
            <div class="stable-photo-stage">
                <img src="{data_uri}" alt="{html.escape(caption or path.name)}">
            </div>
            {caption_html}
        </figure>
        """,
        unsafe_allow_html=True,
    )
