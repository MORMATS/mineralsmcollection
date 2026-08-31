from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from streamlit.testing.v1 import AppTest

from src import db as db_module
from src.db import Base
from src.localities import unmappable_reason
from src.locality_editor import LocalityValidationError, parse_locality_form
from src.models import CollectionItem, Locality, MineralSpecies


PAGE_PATH = Path(__file__).resolve().parents[1] / "views" / "8_Localizaciones.py"


def test_parse_locality_form_normalizes_coordinates_and_country():
    values = parse_locality_form(
        name="  Madrid  ",
        country=" Spain ",
        latitude="40,4168",
        longitude="-3.7038",
    )

    assert values["name"] == "Madrid"
    assert values["country"] == "España"
    assert values["latitude"] == pytest.approx(40.4168)
    assert values["longitude"] == pytest.approx(-3.7038)


@pytest.mark.parametrize(
    ("latitude", "longitude", "message"),
    [
        ("40", "", "latitud y longitud juntas"),
        ("91", "2", "latitud debe estar"),
        ("20", "181", "longitud debe estar"),
        ("norte", "2", "latitud debe ser"),
    ],
)
def test_parse_locality_form_reports_coordinate_errors(latitude, longitude, message):
    with pytest.raises(LocalityValidationError, match=message):
        parse_locality_form(name="Prueba", latitude=latitude, longitude=longitude)


def test_parse_locality_form_requires_geographic_information():
    with pytest.raises(LocalityValidationError, match="Añade al menos"):
        parse_locality_form(notes="Sin origen conocido")


def test_unmappable_reason_distinguishes_missing_invalid_and_unknown_locations():
    assert unmappable_reason(None) == "Sin localidad asignada"
    assert unmappable_reason(SimpleNamespace(
        latitude=40.0,
        longitude=None,
        name="Madrid",
        mine=None,
        region=None,
        country="País desconocido",
    )) == "Coordenadas incompletas"
    assert unmappable_reason(SimpleNamespace(
        latitude=95.0,
        longitude=2.0,
        name="Lugar",
        mine=None,
        region=None,
        country="País desconocido",
    )) == "Coordenadas fuera de rango"
    assert unmappable_reason(SimpleNamespace(
        latitude=None,
        longitude=None,
        name="Lugar remoto",
        mine=None,
        region=None,
        country="País desconocido",
    )) == "Sin coordenadas ni aproximación conocida"


def test_admin_locality_page_shows_relations_and_saves_coordinates(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'localities.sqlite').as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    test_session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "SessionLocal", test_session)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "test-password")

    with test_session() as db:
        mineral = MineralSpecies(name="Amonite")
        locality = Locality(name="Costa fósil", country="País desconocido")
        db.add(
            CollectionItem(
                item_code="FOS-0001",
                item_type="fossil",
                mineral=mineral,
                locality=locality,
                sold=False,
            )
        )
        db.commit()
        locality_id = locality.id

    try:
        app = AppTest.from_file(PAGE_PATH, default_timeout=20)
        app.session_state["admin_unlocked"] = True
        app.run()

        assert not app.exception
        assert any("Amonite" in caption.value for caption in app.caption)
        latitude = next(widget for widget in app.text_input if widget.label == "Latitud")
        longitude = next(widget for widget in app.text_input if widget.label == "Longitud")
        latitude.set_value("43.4")
        longitude.set_value("-8.4")
        next(button for button in app.button if button.label == "Guardar cambios").click().run()

        assert not app.exception
        assert any("guardada correctamente" in success.value for success in app.success)
        with test_session() as db:
            saved = db.scalar(select(Locality).where(Locality.id == locality_id))
            assert saved.latitude == pytest.approx(43.4)
            assert saved.longitude == pytest.approx(-8.4)
    finally:
        engine.dispose()
