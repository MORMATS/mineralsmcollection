from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.settings import get_setting

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    return get_setting(
        "DATABASE_URL",
        "postgresql+psycopg://minerales_user:minerales_password@localhost:5432/minerales",
    )


def get_engine():
    url = get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(
        url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from src import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
