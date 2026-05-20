from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


def get_setting(name: str, default: str | None = None) -> str | None:
    """Return setting from environment first, then Streamlit secrets if available.

    This keeps scripts usable from the terminal while allowing Streamlit Cloud-style
    secrets when the app runs inside Streamlit.
    """
    value = os.getenv(name)
    if value not in (None, ""):
        return value

    try:
        import streamlit as st

        value = st.secrets.get(name)  # type: ignore[attr-defined]
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass

    return default
