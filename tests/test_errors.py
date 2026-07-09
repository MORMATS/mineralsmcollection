from src.errors import is_schema_migration_error


def test_schema_migration_error_detects_postgres_missing_column_message():
    exc = RuntimeError('psycopg.errors.UndefinedColumn: column "item_type" does not exist')

    assert is_schema_migration_error(exc)


def test_schema_migration_error_detects_sqlite_missing_table_message():
    exc = RuntimeError("sqlite3.OperationalError: no such table: collection_items")

    assert is_schema_migration_error(exc)


def test_schema_migration_error_follows_exception_chain():
    cause = RuntimeError("psycopg.errors.UndefinedTable: relation does not exist")
    exc = RuntimeError("wrapped")
    exc.__cause__ = cause

    assert is_schema_migration_error(exc)


def test_schema_migration_error_ignores_unrelated_errors():
    exc = RuntimeError("connection timed out")

    assert not is_schema_migration_error(exc)
