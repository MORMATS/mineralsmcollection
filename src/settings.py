from __future__ import annotations

import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv

load_dotenv()

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _has_local_streamlit_secrets() -> bool:
    candidates = (
        Path.home() / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
    )
    return any(path.exists() for path in candidates)


def get_setting(name: str, default: str | None = None) -> str | None:
    """Return setting from environment first, then Streamlit secrets if available.

    This keeps scripts usable from the terminal while allowing Streamlit Cloud-style
    secrets when the app runs inside Streamlit.
    """
    value = os.getenv(name)
    if value not in (None, ""):
        return value

    if ENV_PATH.exists():
        value = dotenv_values(ENV_PATH).get(name)
        if value not in (None, ""):
            return str(value)

    if _has_local_streamlit_secrets():
        try:
            import streamlit as st

            value = st.secrets.get(name)  # type: ignore[attr-defined]
            if value not in (None, ""):
                return str(value)
        except Exception:
            pass

    return default


def app_env() -> str:
    return str(get_setting("APP_ENV", "development") or "development").strip().lower()


def is_production() -> bool:
    return app_env() == "production"


def get_required_setting(name: str) -> str:
    value = get_setting(name)
    if value in (None, ""):
        raise RuntimeError(f"{name} is required.")
    return value


def get_int_setting(name: str, default: int) -> int:
    value = get_setting(name)
    if value in (None, ""):
        return default
    try:
        return int(str(value))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
