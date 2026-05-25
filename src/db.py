from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.settings import get_int_setting, get_required_setting, get_setting, is_production

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_UPLOAD_DIR = Path("/var/lib/isminerals/uploads") if is_production() else ROOT / "uploads"
UPLOAD_DIR = Path(get_setting("UPLOAD_DIR", str(DEFAULT_UPLOAD_DIR)) or DEFAULT_UPLOAD_DIR)
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    if is_production():
        return get_required_setting("DATABASE_URL")

    default_sqlite = f"sqlite:///{(DATA_DIR / 'isminerals_dev.db').as_posix()}"
    return get_setting("DATABASE_URL", default_sqlite) or default_sqlite


def redact_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<invalid database url>"


def get_engine():
    url = get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine_kwargs = {
        "echo": False,
        "future": True,
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }

    if not url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": get_int_setting("DB_POOL_SIZE", 5),
                "max_overflow": get_int_setting("DB_MAX_OVERFLOW", 10),
                "pool_timeout": get_int_setting("DB_POOL_TIMEOUT", 30),
                "pool_recycle": get_int_setting("DB_POOL_RECYCLE", 1800),
            }
        )

    return create_engine(
        url,
        **engine_kwargs,
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Deprecated compatibility hook.

    Production schema changes are managed with Alembic. Use
    ``python -m alembic upgrade head`` before starting the app.
    """
    return None


def get_session():
    return SessionLocal()
