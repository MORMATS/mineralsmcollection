import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src import mindat_api
from src.db import Base
from src.models import CollectionItem, Locality, MineralSpecies


def test_normalize_mindat_record_extracts_core_fields():
    data = mindat_api.normalize_mindat_record(
        {
            "id": "123",
            "name": "Quartz",
            "formula": "SiO2",
            "elements": "Si, O",
            "hardness": "7",
            "colour": "Colorless",
            "lustre": "Vitreous",
        }
    )

    assert data["mindat_id"] == 123
    assert data["name"] == "Quartz"
    assert data["formula"] == "SiO2"
    assert data["elements"] == "Si, O"
    assert data["hardness_min"] == 7
    assert data["hardness_max"] == 7
    assert data["color"] == "Colorless"
    assert data["luster"] == "Vitreous"


def test_search_mindat_geomaterial_uses_exact_result_and_fetches_detail(monkeypatch):
    calls = []

    def fake_get(path, params=None):
        calls.append((path, params))
        if path == "/geomaterials/":
            return {
                "results": [
                    {"id": 1, "name": "Quartzite"},
                    {"id": 2, "name": "Quartz"},
                ]
            }
        if path == "/geomaterials/2/":
            return {"id": 2, "name": "Quartz", "formula": "SiO2"}
        raise AssertionError(path)

    monkeypatch.setattr(mindat_api, "_mindat_get", fake_get)

    record = mindat_api.search_mindat_geomaterial("Quartz")

    assert record == {"id": 2, "name": "Quartz", "formula": "SiO2"}
    assert calls[0] == ("/geomaterials/", {"format": "json", "q": "Quartz"})
    assert calls[1] == ("/geomaterials/2/", None)


def test_normalize_mindat_locality_record_extracts_coordinates():
    data = mindat_api.normalize_mindat_locality_record(
        {
            "id": "456",
            "name": "Mina Antigua Pilar",
            "region": "Comunidad de Madrid",
            "country": "Spain",
            "lat": "40.5606",
            "long": "-4.0171",
        }
    )

    assert data["mindat_locality_id"] == 456
    assert data["name"] == "Mina Antigua Pilar"
    assert data["region"] == "Comunidad de Madrid"
    assert data["country"] == "Spain"
    assert data["latitude"] == 40.5606
    assert data["longitude"] == -4.0171
    assert data["source_url"] == "https://www.mindat.org/loc-456.html"
    assert '"id": "456"' in data["api_raw_json"]


def test_fetch_mindat_locality_detail_falls_back_to_filtered_list(monkeypatch):
    calls = []

    def fake_get(path, params=None):
        calls.append((path, params))
        if path in ("/localities/456/", "/locality/456/", "/locentries/456/"):
            response = requests.Response()
            response.status_code = 404
            raise requests.HTTPError(response=response)
        if path == "/localities/":
            return {
                "results": [
                    {"id": 123, "txt": "Otra localidad"},
                    {"id": 456, "txt": "Localidad recuperada"},
                ]
            }
        raise AssertionError(path)

    monkeypatch.setattr(mindat_api, "_mindat_get", fake_get)

    record = mindat_api.fetch_mindat_locality_detail(456)

    assert record == {"id": 456, "txt": "Localidad recuperada"}
    assert calls[-1] == (
        "/localities/",
        {"format": "json", "id__in": "456", "page_size": 1},
    )


def test_normalize_mindat_locality_record_parses_txt_hierarchy_with_mine():
    data = mindat_api.normalize_mindat_locality_record(
        {
            "id": 4155,
            "txt": (
                "Silver Mines (Silver Reef), St Arnaud, Northern Grampians Shire, "
                "Victoria, Australia"
            ),
            "country": "Australia",
        }
    )

    assert data["mine"] == "Silver Mines (Silver Reef)"
    assert data["name"] == "St Arnaud"
    assert data["region"] == "Northern Grampians Shire, Victoria"
    assert data["country"] == "Australia"


def test_normalize_mindat_locality_record_parses_txt_hierarchy_without_mine():
    data = mindat_api.normalize_mindat_locality_record(
        {
            "id": 693,
            "txt": (
                "Boxian meteorite, Xiaoyanzhuang, Qiaocheng District, "
                "Bozhou, Anhui, China"
            ),
            "country": "China",
        }
    )

    assert data["mine"] is None
    assert data["name"] == "Boxian meteorite"
    assert data["region"] == "Xiaoyanzhuang, Qiaocheng District, Bozhou, Anhui"
    assert data["country"] == "China"


def test_update_mindat_locality_refreshes_shared_location(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    db = Session(engine, future=True)
    mineral = MineralSpecies(name="Quartz")
    locality = Locality(mindat_locality_id=456, name="Nombre antiguo")
    db.add_all(
        [
            CollectionItem(item_code="MIN-0001", mineral=mineral, locality=locality, sold=False),
            CollectionItem(item_code="MIN-0002", mineral=mineral, locality=locality, sold=False),
        ]
    )
    db.commit()
    monkeypatch.setattr(
        mindat_api,
        "fetch_mindat_locality_detail",
        lambda locality_id: {
            "id": locality_id,
            "name": "Mina Nueva",
            "region": "Madrid",
            "country": "Spain",
            "lat": "40.5",
            "long": "-4.0",
            "description": "Localidad historica",
        },
    )

    updated, message = mindat_api.update_mindat_locality(db, locality)

    assert updated.name == "Mina Nueva"
    assert updated.country == "España"
    assert updated.latitude == 40.5
    assert updated.notes == "Localidad historica"
    assert updated.updated_at is not None
    assert message == "Localizacion actualizada en 2 pieza(s)."
