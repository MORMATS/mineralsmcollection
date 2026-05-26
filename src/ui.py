from __future__ import annotations

import streamlit as st


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

        .admin-corner {
            display: inline-block;
            margin: .35rem 0 1rem;
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
