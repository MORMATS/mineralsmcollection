from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from streamlit.testing.v1 import AppTest

from src import db as db_module
from src import mindat_api
from src.db import Base
from src.localities import unmappable_reason
from src.locality_editor import (
    LocalityValidationError,
    merge_mindat_locality_values,
    parse_locality_form,
)
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


def test_merge_mindat_locality_values_prefers_api_and_keeps_missing_fallbacks():
    values = parse_locality_form(
        mindat_locality_id="456",
        name="Nombre manual",
        mine="Mina manual",
        country="España",
        latitude="40",
        longitude="-3",
        notes="Nota manual",
    )

    merged = merge_mindat_locality_values(
        values,
        {
            "name": "Nombre Mindat",
            "mine": None,
            "region": "Madrid",
            "country": "Spain",
            "latitude": 41.5,
            "longitude": -4.2,
            "notes": "Nota Mindat",
            "source_url": "https://www.mindat.org/loc-456.html",
            "api_raw_json": '{"id": 456}',
        },
    )

    assert merged["mindat_locality_id"] == 456
    assert merged["name"] == "Nombre Mindat"
    assert merged["mine"] == "Mina manual"
    assert merged["region"] == "Madrid"
    assert merged["country"] == "España"
    assert merged["latitude"] == pytest.approx(41.5)
    assert merged["longitude"] == pytest.approx(-4.2)
    assert merged["notes"] == "Nota Mindat"
    assert merged["source_url"] == "https://www.mindat.org/loc-456.html"
    assert merged["api_raw_json"] == '{"id": 456}'
    assert merged["normalized_key"] == "mindat:456"


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


def test_admin_locality_page_refreshes_details_when_mindat_id_changes(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'mindat-refresh.sqlite').as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    test_session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "SessionLocal", test_session)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "test-password")
    monkeypatch.setattr(
        mindat_api,
        "get_mindat_locality_data",
        lambda locality_id: {
            "mindat_locality_id": locality_id,
            "name": "Localidad Mindat",
            "mine": "Mina Mindat",
            "region": "Madrid",
            "country": "Spain",
            "latitude": 40.5,
            "longitude": -4.0,
            "notes": "Datos remotos",
            "source_url": f"https://www.mindat.org/loc-{locality_id}.html",
            "api_raw_json": f'{{"id": {locality_id}}}',
        },
    )

    with test_session() as db:
        locality = Locality(name="Nombre antiguo", country="España")
        db.add(locality)
        db.commit()
        locality_id = locality.id

    try:
        app = AppTest.from_file(PAGE_PATH, default_timeout=20)
        app.session_state["admin_unlocked"] = True
        app.run()

        mindat_id = next(
            widget for widget in app.text_input if widget.label == "ID de localidad en Mindat"
        )
        mindat_id.set_value("456")
        next(button for button in app.button if button.label == "Guardar cambios").click().run()

        assert not app.exception
        assert any("actualizada desde Mindat" in success.value for success in app.success)
        with test_session() as db:
            saved = db.scalar(select(Locality).where(Locality.id == locality_id))
            assert saved.mindat_locality_id == 456
            assert saved.name == "Localidad Mindat"
            assert saved.mine == "Mina Mindat"
            assert saved.country == "España"
            assert saved.latitude == pytest.approx(40.5)
            assert saved.source_url == "https://www.mindat.org/loc-456.html"
            assert saved.api_raw_json == '{"id": 456}'
    finally:
        engine.dispose()
