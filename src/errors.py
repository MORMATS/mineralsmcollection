from __future__ import annotations


SCHEMA_MIGRATION_ERROR_MARKERS = (
    "undefinedcolumn",
    "undefinedtable",
    "no such column",
    "no such table",
    "column does not exist",
    "relation does not exist",
)


def is_schema_migration_error(exc: BaseException) -> bool:
    """Return True for common database errors caused by pending migrations."""
    seen: set[int] = set()
    current: BaseException | None = exc

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = f"{current.__class__.__name__} {current}".lower()
        if any(marker in text for marker in SCHEMA_MIGRATION_ERROR_MARKERS):
            return True
        current = current.__cause__ or current.__context__

    return False
