from __future__ import annotations


ITEM_TYPE_MINERAL = "mineral"
ITEM_TYPE_PENDANT = "pendant"
ITEM_TYPE_FOSSIL = "fossil"
DEFAULT_ITEM_TYPE = ITEM_TYPE_MINERAL

ITEM_TYPE_LABELS = {
    ITEM_TYPE_MINERAL: "Mineral",
    ITEM_TYPE_PENDANT: "Colgante",
    ITEM_TYPE_FOSSIL: "Fósil",
}

ITEM_TYPE_PLURAL_LABELS = {
    ITEM_TYPE_MINERAL: "Minerales",
    ITEM_TYPE_PENDANT: "Colgantes",
    ITEM_TYPE_FOSSIL: "Fósiles",
}

ITEM_TYPE_FILTER_ALL = "Todos"
ITEM_TYPE_FILTER_OPTIONS = [
    ITEM_TYPE_FILTER_ALL,
    ITEM_TYPE_PLURAL_LABELS[ITEM_TYPE_MINERAL],
    ITEM_TYPE_PLURAL_LABELS[ITEM_TYPE_PENDANT],
    ITEM_TYPE_PLURAL_LABELS[ITEM_TYPE_FOSSIL],
]

_FILTER_LABEL_TO_VALUE = {
    ITEM_TYPE_PLURAL_LABELS[ITEM_TYPE_MINERAL]: ITEM_TYPE_MINERAL,
    ITEM_TYPE_PLURAL_LABELS[ITEM_TYPE_PENDANT]: ITEM_TYPE_PENDANT,
    ITEM_TYPE_PLURAL_LABELS[ITEM_TYPE_FOSSIL]: ITEM_TYPE_FOSSIL,
}


def normalize_item_type(value: str | None) -> str:
    clean_value = str(value or "").strip().lower()
    if clean_value in {"pendant", "colgante", "colgantes"}:
        return ITEM_TYPE_PENDANT
    if clean_value in {"fossil", "fossils", "fósil", "fósiles", "fosil", "fosiles"}:
        return ITEM_TYPE_FOSSIL
    return ITEM_TYPE_MINERAL


def item_type_label(value: str | None, *, plural: bool = False) -> str:
    normalized = normalize_item_type(value)
    labels = ITEM_TYPE_PLURAL_LABELS if plural else ITEM_TYPE_LABELS
    return labels[normalized]


def item_type_from_filter(label: str | None) -> str | None:
    return _FILTER_LABEL_TO_VALUE.get(str(label or "").strip())


def item_type_filter_label(value: str | None) -> str:
    if not value:
        return ITEM_TYPE_FILTER_ALL
    return item_type_label(value, plural=True)
