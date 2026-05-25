from src import mindat_api


def test_normalize_mindat_record_extracts_core_fields():
    data = mindat_api.normalize_mindat_record(
        {
            "id": "123",
            "name": "Quartz",
            "formula": "SiO2",
            "hardness": "7",
            "colour": "Colorless",
            "lustre": "Vitreous",
        }
    )

    assert data["mindat_id"] == 123
    assert data["name"] == "Quartz"
    assert data["formula"] == "SiO2"
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
