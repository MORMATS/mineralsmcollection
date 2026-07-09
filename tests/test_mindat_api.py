from src import mindat_api


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
