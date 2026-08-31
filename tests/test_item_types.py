from src.item_types import (
    ITEM_TYPE_FILTER_ALL,
    item_type_filter_label,
    item_type_from_filter,
    item_type_label,
    normalize_item_type,
)


def test_normalize_item_type_defaults_to_mineral():
    assert normalize_item_type(None) == "mineral"
    assert normalize_item_type("unknown") == "mineral"


def test_normalize_item_type_accepts_spanish_pendant_label():
    assert normalize_item_type("Colgante") == "pendant"
    assert normalize_item_type("colgantes") == "pendant"


def test_normalize_item_type_accepts_fossil_labels():
    assert normalize_item_type("Fósil") == "fossil"
    assert normalize_item_type("fosiles") == "fossil"


def test_item_type_labels_are_public_spanish_labels():
    assert item_type_label("mineral") == "Mineral"
    assert item_type_label("pendant") == "Colgante"
    assert item_type_label("pendant", plural=True) == "Colgantes"
    assert item_type_label("fossil") == "Fósil"
    assert item_type_label("fossil", plural=True) == "Fósiles"


def test_item_type_filter_helpers_translate_selectbox_labels():
    assert item_type_from_filter(ITEM_TYPE_FILTER_ALL) is None
    assert item_type_from_filter("Minerales") == "mineral"
    assert item_type_from_filter("Colgantes") == "pendant"
    assert item_type_from_filter("Fósiles") == "fossil"
    assert item_type_filter_label(None) == ITEM_TYPE_FILTER_ALL
    assert item_type_filter_label("pendant") == "Colgantes"
