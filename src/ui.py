from __future__ import annotations

import base64
import hashlib
import html
import mimetypes
from pathlib import Path
from statistics import median
from textwrap import dedent
from typing import Iterable

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

from src.item_types import item_type_label, normalize_item_type


CARD_THUMBNAIL_DIR = Path(__file__).resolve().parents[1] / "data" / "image_thumbnails"
CARD_THUMBNAIL_SIZE = (520, 562)
CARD_THUMBNAIL_QUALITY = 76


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


def type_class(item_type: str | None) -> str:
    return f"is-{normalize_item_type(item_type)}"


def render_html(markup: str) -> None:
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def render_global_styles() -> None:
    render_html(
        """
        <style>
        :root {
            --m4w-primary: #f6f0e6;
            --m4w-surface: #fffaf2;
            --m4w-surface-muted: #ede8de;
            --m4w-accent: #153a5b;
            --m4w-accent-2: #1e5080;
            --m4w-border: #c4a882;
            --m4w-text: #3c2f2f;
            --m4w-text-light: #6b4e2e;
            --m4w-success: #1a5c3a;
            --m4w-danger: #8b1a1a;
            --m4w-warn: #6b4a0f;
            --m4w-shadow: 0 10px 24px rgba(21, 58, 91, .10);
            --m4w-shadow-soft: 0 1px 0 rgba(61, 47, 47, .06);

            --mineral-bg: var(--m4w-primary);
            --mineral-bg-soft: var(--m4w-surface-muted);
            --mineral-panel: var(--m4w-surface);
            --mineral-panel-warm: var(--m4w-surface-muted);
            --mineral-ink: var(--m4w-text);
            --mineral-soft-ink: var(--m4w-text-light);
            --mineral-muted: var(--m4w-text-light);
            --mineral-line: var(--m4w-border);
            --mineral-line-strong: var(--m4w-border);
            --mineral-forest: var(--m4w-accent);
            --mineral-forest-soft: rgba(21, 58, 91, .08);
            --mineral-brass: var(--m4w-accent);
            --mineral-brass-soft: var(--m4w-surface-muted);
            --mineral-rust: var(--m4w-danger);
            --mineral-teal: var(--m4w-accent-2);
            --mineral-shadow: var(--m4w-shadow);
            --mineral-shadow-soft: var(--m4w-shadow-soft);
        }

        .stApp {
            background: var(--m4w-primary);
            color: var(--mineral-ink);
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            letter-spacing: 0;
        }

        .main .block-container {
            max-width: 1180px;
            padding-top: 1.15rem;
            padding-bottom: 3rem;
        }

        * {
            letter-spacing: 0;
        }

        h1, h2, h3, h4 {
            letter-spacing: 0;
            color: var(--m4w-accent) !important;
            font-weight: 800;
        }

        h1 {
            font-size: clamp(1.7rem, 2.6vw, 2.25rem) !important;
        }

        h2 {
            font-size: clamp(1.25rem, 2vw, 1.6rem) !important;
        }

        h3 {
            font-size: 1.05rem !important;
        }

        p {
            color: var(--mineral-soft-ink);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--m4w-primary) 0%, var(--m4w-surface-muted) 100%) !important;
            border-right: 1px solid var(--m4w-border) !important;
        }

        [data-testid="stSidebar"] * {
            color: var(--m4w-text) !important;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--m4w-accent) !important;
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: .55rem;
        }

        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            min-height: 34px;
            border-radius: 8px !important;
            border: 1px solid transparent;
            font-weight: 700 !important;
            transition: background .16s ease, border-color .16s ease, color .16s ease;
        }

        [data-testid="stSidebarNav"] a:hover,
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: rgba(21, 58, 91, .08) !important;
            border-color: rgba(21, 58, 91, .16);
        }

        [data-testid="stSidebarNav"] a[aria-current="page"],
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: var(--m4w-accent) !important;
            border-color: var(--m4w-accent) !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] *,
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) * {
            color: #ffffff !important;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(180deg, var(--m4w-surface) 0%, var(--m4w-surface-muted) 100%) !important;
            border: 1px solid var(--m4w-border) !important;
            border-top: 3px solid var(--m4w-accent) !important;
            border-radius: 8px !important;
            padding: .9rem 1rem !important;
            box-shadow: var(--m4w-shadow-soft);
        }

        [data-testid="stMetric"] label,
        [data-testid="stMetric"] [data-testid="stMetricLabel"] p {
            color: var(--m4w-text-light) !important;
            font-size: .72rem !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--m4w-accent) !important;
            font-weight: 850 !important;
        }

        div.stButton > button,
        div.stFormSubmitButton > button,
        div[data-testid="stLinkButton"] > a,
        .stDownloadButton > button {
            min-height: 2.45rem;
            border-radius: 8px !important;
            border: 1px solid var(--m4w-accent) !important;
            color: #ffffff !important;
            background: var(--m4w-accent) !important;
            box-shadow: none;
            font-weight: 750 !important;
            transition: border-color .14s ease, color .14s ease, background .14s ease, transform .14s ease;
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
            border-color: #0f2c45 !important;
            color: #ffffff !important;
            background: #0f2c45 !important;
            transform: translateY(-1px);
        }

        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primaryFormSubmit"],
        button[data-testid="stBaseButton-primaryFormSubmit"],
        div.stButton > button[data-testid="baseButton-primary"] {
            background: var(--m4w-accent) !important;
            border-color: var(--m4w-accent) !important;
            color: #ffffff !important;
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
            background: #0f2c45 !important;
            color: #ffffff !important;
        }

        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"],
        [data-testid="stMultiSelect"] > div > div,
        [data-testid="stDateInput"] input,
        [data-testid="stTextArea"] textarea {
            background-color: var(--m4w-surface) !important;
            border: 1px solid rgba(196, 168, 130, .95) !important;
            border-radius: 8px !important;
            color: var(--m4w-text) !important;
            box-shadow: none !important;
        }

        [data-testid="stFileUploader"] section {
            border-radius: 8px !important;
            border-color: var(--m4w-border) !important;
            background: rgba(255, 250, 242, .78) !important;
        }

        [data-testid="stAlert"][data-baseweb="notification"] {
            border: 1px solid rgba(196, 168, 130, .75) !important;
            border-radius: 8px !important;
        }

        [data-testid="stInfo"] {
            background: rgba(21, 58, 91, .08) !important;
            border-left: 4px solid var(--m4w-accent) !important;
        }

        [data-testid="stSuccess"] {
            background: rgba(26, 92, 58, .10) !important;
            border-left: 4px solid var(--m4w-success) !important;
        }

        [data-testid="stWarning"] {
            background: rgba(107, 74, 15, .10) !important;
            border-left: 4px solid var(--m4w-warn) !important;
        }

        [data-testid="stError"] {
            background: rgba(139, 26, 26, .10) !important;
            border-left: 4px solid var(--m4w-danger) !important;
        }

        [data-testid="stExpander"] {
            background: rgba(255, 250, 242, .75) !important;
            border: 1px solid var(--m4w-border) !important;
            border-radius: 8px !important;
        }

        [data-testid="stExpander"] summary {
            color: var(--m4w-accent) !important;
            font-weight: 750 !important;
        }

        [data-testid="stDataFrame"] > div,
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--m4w-border) !important;
            border-radius: 8px !important;
            background: rgba(255, 250, 242, .72) !important;
            box-shadow: var(--m4w-shadow-soft);
        }

        .stTabs [data-baseweb="tab"] p {
            color: var(--m4w-text-light);
            font-weight: 750;
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] p {
            color: var(--m4w-accent);
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--m4w-accent);
        }

        .premium-hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(196, 168, 130, .85);
            border-left: 4px solid var(--m4w-accent);
            border-radius: 8px;
            background: rgba(246, 240, 230, .96);
            box-shadow: var(--m4w-shadow);
            padding: clamp(.85rem, 2.2vw, 1.25rem) clamp(.95rem, 2.5vw, 1.35rem);
            margin-bottom: 1.05rem;
            backdrop-filter: blur(10px);
        }

        .premium-hero::after {
            content: none;
        }

        .premium-hero > * {
            position: relative;
            z-index: 1;
        }

        .hero-kicker,
        .section-kicker {
            color: var(--m4w-text-light);
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: 0;
            margin: 0 0 .22rem;
            text-transform: uppercase;
        }

        .hero-title,
        .section-title {
            color: var(--m4w-accent);
            font-weight: 850;
        }

        .hero-title {
            font-size: clamp(1.75rem, 3.3vw, 2.45rem);
            line-height: 1.05;
            margin: 0;
            max-width: 100%;
        }

        .hero-copy {
            color: var(--m4w-text-light);
            font-size: clamp(.92rem, 1.6vw, 1.02rem);
            font-weight: 600;
            line-height: 1.45;
            max-width: 62rem;
            margin: .45rem 0 0;
        }

        .hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: 1.15rem;
        }

        .premium-chip,
        .status-chip,
        .type-chip {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            min-height: 1.8rem;
            padding: .22rem .58rem;
            border-radius: 8px;
            border: 1px solid rgba(21, 58, 91, .22);
            background: rgba(21, 58, 91, .08);
            color: var(--m4w-accent);
            font-size: .8rem;
            font-weight: 750;
            line-height: 1.2;
        }

        .status-chip.is-available {
            border-color: rgba(26, 92, 58, .24);
            background: rgba(26, 92, 58, .10);
            color: var(--m4w-success);
        }

        .status-chip.is-sold {
            border-color: rgba(139, 26, 26, .24);
            background: rgba(139, 26, 26, .10);
            color: var(--m4w-danger);
        }

        .type-chip.is-mineral {
            border-color: rgba(21, 58, 91, .25);
            background: rgba(21, 58, 91, .10);
            color: var(--m4w-accent);
        }

        .type-chip.is-pendant {
            border-color: rgba(196, 168, 130, .55);
            background: rgba(196, 168, 130, .18);
            color: var(--m4w-text);
        }

        .type-chip.is-fossil {
            border-color: rgba(174, 91, 45, .38);
            background: rgba(174, 91, 45, .13);
            color: #8a4728;
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
            border: 1px solid var(--m4w-border);
            border-radius: 8px;
            background: linear-gradient(180deg, var(--m4w-surface) 0%, var(--m4w-surface-muted) 100%);
            box-shadow: var(--m4w-shadow-soft);
        }

        .metric-card {
            border-top: 3px solid var(--m4w-accent);
            padding: .85rem .95rem;
        }

        .metric-label {
            color: var(--m4w-text-light);
            font-size: .72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0;
            margin: 0 0 .25rem;
        }

        .metric-value {
            color: var(--m4w-accent);
            font-size: 1.85rem;
            line-height: 1;
            font-weight: 850;
            margin: 0;
        }

        .metric-note {
            color: var(--m4w-text-light);
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
            font-size: clamp(1.3rem, 2.2vw, 1.65rem);
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
            color: var(--m4w-text-light);
            font-size: .76rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: .4rem;
        }

        .collection-card {
            overflow: hidden;
            border: 1px solid var(--m4w-border);
            border-radius: 8px;
            background: var(--m4w-surface);
            box-shadow: var(--m4w-shadow-soft);
            margin-bottom: .55rem;
        }

        .collection-visual {
            position: relative;
            aspect-ratio: 1 / 1.08;
            overflow: hidden;
            background: linear-gradient(145deg, rgba(21, 58, 91, .10), rgba(196, 168, 130, .22)), var(--m4w-surface-muted);
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
            background: linear-gradient(145deg, rgba(21, 58, 91, .10), rgba(196, 168, 130, .20)), var(--m4w-surface-muted);
            color: var(--m4w-accent);
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
            border: 1px solid rgba(21, 58, 91, .24);
            border-radius: 999px;
            background: rgba(255, 250, 242, .78);
            color: var(--m4w-accent);
            font-size: 2.2rem;
            font-weight: 850;
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

        .collection-type {
            position: absolute;
            top: .65rem;
            right: .65rem;
        }

        .collection-body {
            padding: .8rem .85rem .9rem;
        }

        .collection-title {
            color: var(--m4w-text);
            font-size: 1rem;
            font-weight: 800;
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
            color: var(--m4w-accent);
            font-size: .76rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: .28rem;
        }

        .native-photo-placeholder,
        .premium-photo-placeholder {
            aspect-ratio: 1 / var(--photo-frame-ratio, 1);
            border: 1px solid var(--m4w-border);
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
            border: 1px solid var(--m4w-border);
            background: linear-gradient(145deg, rgba(255, 250, 242, .88), rgba(237, 232, 222, .88)), var(--m4w-surface);
            box-shadow: var(--m4w-shadow-soft);
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
            color: var(--m4w-text-light);
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
            margin: 0 0 .25rem;
        }

        .detail-value {
            color: var(--m4w-text);
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
            border: 1px solid var(--m4w-border);
            border-radius: 8px;
            background: var(--m4w-surface);
            box-shadow: var(--m4w-shadow-soft);
        }

        .wiki-photo-media {
            width: 100%;
            min-height: 14rem;
            background:
                linear-gradient(145deg, rgba(21, 58, 91, .12), rgba(196, 168, 130, .20)),
                var(--wiki-photo-url),
                var(--m4w-surface-muted);
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
            color: var(--m4w-accent);
            background: rgba(246, 240, 230, .92);
            border: 1px solid var(--m4w-border);
            font-size: .72rem;
            font-weight: 800;
            line-height: 1;
            text-decoration: none;
        }

        .admin-corner:hover {
            color: #ffffff;
            background: var(--m4w-accent);
            border-color: var(--m4w-accent);
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

        /* Visual refresh: mineral-gallery palette, softer hierarchy and clear controls. */
        :root {
            --app-bg: #f3f5f1;
            --app-surface: #ffffff;
            --app-surface-soft: #e9efeb;
            --app-pine: #173c35;
            --app-pine-deep: #0d2b27;
            --app-sage: #6f8d7f;
            --app-copper: #c8783e;
            --app-copper-soft: #f5e7db;
            --app-ink: #1d2925;
            --app-muted: #62706a;
            --app-line: #d8e1dc;
            --app-shadow: 0 18px 48px rgba(19, 55, 48, .09);
            --app-shadow-soft: 0 6px 22px rgba(19, 55, 48, .07);
        }

        .stApp {
            background:
                radial-gradient(circle at 88% 4%, rgba(200, 120, 62, .09), transparent 24rem),
                radial-gradient(circle at 58% 28%, rgba(111, 141, 127, .08), transparent 30rem),
                var(--app-bg);
            color: var(--app-ink);
            font-family: Inter, Aptos, "Segoe UI", sans-serif;
        }

        .main .block-container {
            max-width: 1240px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3, h4 {
            color: var(--app-pine) !important;
            font-weight: 760;
            letter-spacing: -.025em;
        }

        p { color: var(--app-muted); }

        section[data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 20% 4%, rgba(200, 120, 62, .19), transparent 12rem),
                linear-gradient(180deg, var(--app-pine-deep), #12342f 72%, #173c35) !important;
            border-right: 0 !important;
            box-shadow: 8px 0 36px rgba(13, 43, 39, .12);
        }

        section[data-testid="stSidebar"] * {
            color: rgba(255, 255, 255, .78) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > div:first-child {
            padding-top: 1.4rem;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span {
            font-size: .78rem;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            min-height: 42px;
            margin: .14rem .55rem;
            padding-inline: .8rem;
            border: 1px solid transparent !important;
            border-radius: 11px !important;
            font-weight: 650 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            background: rgba(255, 255, 255, .08) !important;
            border-color: rgba(255, 255, 255, .08) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: rgba(255, 255, 255, .95) !important;
            border-color: rgba(255, 255, 255, .95) !important;
            box-shadow: 0 8px 22px rgba(0, 0, 0, .12);
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] * {
            color: var(--app-pine-deep) !important;
        }

        .premium-hero {
            isolation: isolate;
            min-height: 12rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border: 0;
            border-radius: 24px;
            background:
                linear-gradient(118deg, rgba(13, 43, 39, .98), rgba(23, 60, 53, .96) 58%, rgba(43, 82, 70, .93));
            box-shadow: var(--app-shadow);
            padding: clamp(1.55rem, 4vw, 2.8rem);
            margin-bottom: 1.25rem;
        }

        .premium-hero::before,
        .premium-hero::after {
            content: "";
            position: absolute;
            z-index: -1;
            border: 1px solid rgba(255, 255, 255, .14);
            transform: rotate(28deg);
        }

        .premium-hero::before {
            width: 15rem;
            height: 15rem;
            right: -3rem;
            top: -7rem;
            border-radius: 44% 56% 42% 58%;
            background: linear-gradient(145deg, rgba(200, 120, 62, .38), rgba(255, 255, 255, .02));
        }

        .premium-hero::after {
            width: 8rem;
            height: 8rem;
            right: 10rem;
            bottom: -5.5rem;
            border-radius: 38% 62% 58% 42%;
            background: rgba(111, 141, 127, .26);
        }

        .hero-kicker {
            color: #e4a477;
            letter-spacing: .12em;
        }

        .hero-title {
            color: #ffffff;
            font-size: clamp(2.2rem, 4.5vw, 4rem);
            letter-spacing: -.045em;
            max-width: 44rem;
        }

        .hero-copy {
            color: rgba(255, 255, 255, .76);
            max-width: 47rem;
            font-weight: 450;
            line-height: 1.6;
        }

        .premium-hero .premium-chip {
            color: rgba(255, 255, 255, .88);
            border-color: rgba(255, 255, 255, .17);
            background: rgba(255, 255, 255, .08);
        }

        .premium-chip,
        .status-chip,
        .type-chip {
            min-height: 1.75rem;
            border-radius: 999px;
            padding: .25rem .66rem;
            font-size: .76rem;
        }

        .section-heading {
            align-items: center;
            margin: 2rem 0 .8rem;
        }

        .section-kicker {
            color: var(--app-copper);
            letter-spacing: .1em;
        }

        .section-title {
            color: var(--app-pine);
            font-size: clamp(1.35rem, 2.3vw, 1.8rem);
            letter-spacing: -.03em;
        }

        .metric-strip {
            gap: .85rem;
            margin: 1.15rem 0 1.25rem;
        }

        .metric-card,
        .detail-card,
        .info-panel,
        .filter-shell {
            border: 1px solid var(--app-line);
            border-radius: 16px;
            background: rgba(255, 255, 255, .9);
            box-shadow: var(--app-shadow-soft);
        }

        .metric-card {
            position: relative;
            overflow: hidden;
            border-top: 1px solid var(--app-line);
            padding: 1.05rem 1.1rem;
        }

        .metric-card::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 4px;
            background: linear-gradient(var(--app-copper), #dda679);
        }

        .metric-label { color: var(--app-sage); letter-spacing: .07em; }
        .metric-value { color: var(--app-pine); font-size: 2rem; }
        .metric-note { color: var(--app-muted); }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--app-line) !important;
            border-radius: 18px !important;
            background: rgba(255, 255, 255, .76) !important;
            box-shadow: var(--app-shadow-soft);
        }

        div.stButton > button,
        div.stFormSubmitButton > button,
        div[data-testid="stLinkButton"] > a,
        .stDownloadButton > button {
            min-height: 2.7rem;
            border-radius: 11px !important;
            border: 1px solid var(--app-line) !important;
            color: var(--app-pine) !important;
            background: rgba(255, 255, 255, .92) !important;
            box-shadow: 0 2px 8px rgba(19, 55, 48, .04);
            font-weight: 680 !important;
        }

        div.stButton > button:hover,
        div.stFormSubmitButton > button:hover,
        div[data-testid="stLinkButton"] > a:hover,
        .stDownloadButton > button:hover {
            border-color: var(--app-sage) !important;
            color: var(--app-pine-deep) !important;
            background: var(--app-surface-soft) !important;
            transform: translateY(-1px);
            box-shadow: 0 7px 16px rgba(19, 55, 48, .09);
        }

        div.stButton > button:disabled,
        div.stFormSubmitButton > button:disabled,
        .stDownloadButton > button:disabled {
            color: var(--app-muted) !important;
            background: #edf1ef !important;
            border-color: var(--app-line) !important;
            box-shadow: none !important;
            cursor: not-allowed;
            opacity: .58;
            transform: none;
        }

        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primaryFormSubmit"],
        button[data-testid="stBaseButton-primaryFormSubmit"],
        div.stButton > button[data-testid="baseButton-primary"] {
            color: #ffffff !important;
            background: var(--app-pine) !important;
            border-color: var(--app-pine) !important;
            box-shadow: 0 7px 18px rgba(23, 60, 53, .18);
        }

        div.stButton > button[kind="primary"]:hover,
        div.stFormSubmitButton > button[kind="primaryFormSubmit"]:hover,
        button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
            color: #ffffff !important;
            background: var(--app-pine-deep) !important;
            border-color: var(--app-pine-deep) !important;
        }

        button:focus-visible,
        input:focus-visible,
        textarea:focus-visible,
        [role="combobox"]:focus-visible {
            outline: 3px solid rgba(200, 120, 62, .28) !important;
            outline-offset: 2px;
        }

        [data-baseweb="input"],
        [data-baseweb="textarea"],
        [data-baseweb="select"],
        [data-testid="stMultiSelect"] > div > div {
            border-radius: 11px !important;
        }

        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"],
        [data-testid="stMultiSelect"] > div > div,
        [data-testid="stDateInput"] input,
        [data-testid="stTextArea"] textarea {
            background-color: #ffffff !important;
            border-color: var(--app-line) !important;
            color: var(--app-ink) !important;
        }

        .collection-card {
            border-color: var(--app-line);
            border-radius: 17px;
            background: var(--app-surface);
            box-shadow: var(--app-shadow-soft);
            transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
        }

        .collection-card:hover {
            transform: translateY(-4px);
            border-color: #c5d3cb;
            box-shadow: 0 18px 34px rgba(19, 55, 48, .13);
        }

        .collection-visual {
            background: linear-gradient(145deg, #e1e9e4, #f4e9df);
        }

        .collection-placeholder,
        .native-photo-placeholder,
        .premium-photo-placeholder {
            background:
                radial-gradient(circle at 36% 34%, rgba(255, 255, 255, .85), transparent 24%),
                linear-gradient(145deg, #dfe9e3, #f3e4d8);
        }

        .collection-placeholder-initial,
        .premium-photo-placeholder-initial,
        .native-photo-placeholder span {
            border-color: rgba(23, 60, 53, .14);
            background: rgba(255, 255, 255, .72);
            color: var(--app-pine);
        }

        .collection-body { padding: 1rem 1rem 1.05rem; }
        .collection-code { color: var(--app-copper); letter-spacing: .06em; }
        .collection-title { color: var(--app-pine); font-size: 1.03rem; }
        .collection-meta { color: var(--app-muted); }

        .detail-card { background: #ffffff; }
        .detail-label { color: var(--app-sage); letter-spacing: .07em; }
        .detail-value { color: var(--app-ink); }

        [data-testid="stAlert"][data-baseweb="notification"],
        [data-testid="stExpander"] {
            border-radius: 13px !important;
            border-color: var(--app-line) !important;
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] p { color: var(--app-pine); }
        .stTabs [data-baseweb="tab-highlight"] { background-color: var(--app-copper); }

        .admin-corner {
            color: rgba(255, 255, 255, .64);
            background: var(--app-pine-deep);
            border-color: rgba(255, 255, 255, .12);
            border-radius: 9px;
        }

        @media (max-width: 760px) {
            .main .block-container { padding-top: .8rem; }
            .premium-hero { min-height: 10rem; border-radius: 18px; padding: 1.4rem; }
            .premium-hero::after { display: none; }
            .hero-title { font-size: 2.35rem; }
            .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
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


def render_type_chip(item_type: str | None) -> str:
    return f'<span class="type-chip {type_class(item_type)}">{item_type_label(item_type)}</span>'


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
    item_type: str | None = None,
    title: str,
    mineral_name: str,
    country: str | None,
    sold: bool,
    cover_path: Path | None,
) -> None:
    image_html = ""
    if cover_path and cover_path.exists():
        data_uri = _collection_thumbnail_data_uri(str(cover_path), cover_path.stat().st_mtime_ns)
        if data_uri:
            image_html = (
                f'<img src="{data_uri}" alt="{escape_html(title)}" '
                'loading="lazy" decoding="async" fetchpriority="low">'
            )

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
                <div class="collection-type">{render_type_chip(item_type)}</div>
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


def _thumbnail_cache_path(path: Path, mtime_ns: int, size: tuple[int, int]) -> Path:
    digest = hashlib.sha1(f"{path.resolve()}:{mtime_ns}:{size[0]}x{size[1]}".encode("utf-8")).hexdigest()
    return CARD_THUMBNAIL_DIR / f"{digest}.jpg"


def _save_collection_thumbnail(source_path: Path, cache_path: Path, size: tuple[int, int]) -> bool:
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

            thumbnail = ImageOps.fit(image, size, method=resample)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            thumbnail.save(cache_path, format="JPEG", quality=CARD_THUMBNAIL_QUALITY, optimize=True, progressive=True)
            return True
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return False


@st.cache_data(show_spinner=False)
def _collection_thumbnail_data_uri(path_text: str, mtime_ns: int) -> str | None:
    path = Path(path_text)
    if not path.exists():
        return None

    cache_path = _thumbnail_cache_path(path, mtime_ns, CARD_THUMBNAIL_SIZE)
    if not cache_path.exists() and not _save_collection_thumbnail(path, cache_path, CARD_THUMBNAIL_SIZE):
        return None

    encoded = base64.b64encode(cache_path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


@st.cache_data(show_spinner=False)
def _image_data_uri(path_text: str, mtime_ns: int) -> str | None:
    path = Path(path_text)
    if not path.exists():
        return None

    mime_type = mimetypes.guess_type(path.name)[0] or "image/webp"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def image_data_uri(path: Path) -> str | None:
    if not path.exists():
        return None
    return _image_data_uri(str(path), path.stat().st_mtime_ns)


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
