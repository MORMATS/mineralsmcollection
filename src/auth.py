from __future__ import annotations

import hashlib
import hmac
import secrets

import streamlit as st

from src.settings import get_setting
from src.ui import render_page_header


ADMIN_PASSWORD_ENV = "ADMIN_PASSWORD_HASH"
HASH_PREFIX = "pbkdf2_sha256"
HASH_ITERATIONS = 600_000


def hash_admin_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        HASH_ITERATIONS,
    ).hex()
    return f"{HASH_PREFIX}:{HASH_ITERATIONS}:{salt}:{digest}"


def verify_admin_password(password: str, stored_hash: str | None = None) -> bool:
    stored_hash = stored_hash or get_admin_password_hash()
    if not stored_hash:
        return False

    if not stored_hash.startswith(f"{HASH_PREFIX}:"):
        return hmac.compare_digest(password, stored_hash)

    try:
        prefix, iterations_text, salt, expected_digest = stored_hash.split(":", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False

    if prefix != HASH_PREFIX:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    ).hex()
    return hmac.compare_digest(digest, expected_digest)


def get_admin_password_hash() -> str | None:
    return get_setting(ADMIN_PASSWORD_ENV, "")


def admin_password_configured() -> bool:
    return bool(get_admin_password_hash())


def admin_unlocked() -> bool:
    return bool(st.session_state.get("admin_unlocked")) and admin_password_configured()


def lock_admin() -> None:
    st.session_state["admin_unlocked"] = False


def render_admin_sidebar() -> None:
    login_requested = st.query_params.get("admin") == "1"

    if not admin_unlocked() and not login_requested:
        st.markdown(
            '<a class="admin-corner" href="?admin=1" target="_self">Admin</a>',
            unsafe_allow_html=True,
        )
        return

    with st.sidebar:
        with st.expander("Admin", expanded=login_requested and not admin_unlocked()):
            if admin_unlocked():
                st.caption("Acceso activo")
                if st.button("Bloquear", key="admin_lock"):
                    lock_admin()
                    st.rerun()
                return

            if admin_password_configured():
                _render_unlock_form("sidebar")
            else:
                st.caption("ADMIN_PASSWORD_HASH no esta configurado.")


def require_admin_access() -> None:
    if admin_unlocked():
        return

    render_page_header(
        "Administracion",
        "Acceso protegido",
        "Introduce la contrasena de administracion para continuar.",
        meta=["Zona privada", "Control de edicion"],
    )
    if admin_password_configured():
        _render_unlock_form("main")
    else:
        st.error("ADMIN_PASSWORD_HASH no esta configurado en el entorno.")

    st.stop()


def _render_unlock_form(key_prefix: str) -> None:
    with st.form(f"{key_prefix}_admin_unlock"):
        password = st.text_input("Contrasena", type="password", key=f"{key_prefix}_admin_password")
        submitted = st.form_submit_button("Desbloquear")

    if not submitted:
        return

    if verify_admin_password(password):
        st.session_state["admin_unlocked"] = True
        st.rerun()

    st.error("Contrasena incorrecta.")
