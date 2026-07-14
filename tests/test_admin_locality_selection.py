from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from streamlit.testing.v1 import AppTest

from src import db as db_module
from src import image_utils
from src.db import Base
from src.models import CollectionItem, Locality, MineralSpecies


PAGE_PATH = Path(__file__).resolve().parents[1] / "views" / "3_Alta_edicion.py"
NEW_LOCALITY_OPTION = "__new_locality__"
NO_LOCALITY_OPTION = "__no_locality__"
LOCALITY_OPTION_PREFIX = "locality:"


def locality_option(locality_id: int) -> str:
    return f"{LOCALITY_OPTION_PREFIX}{locality_id}"


def prepare_database(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'ui.sqlite').as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    test_session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)

    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(db_module, "SessionLocal", test_session)
    monkeypatch.setattr(db_module, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(image_utils, "UPLOAD_DIR", upload_dir)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "test-password")

    with test_session() as db:
        mineral = MineralSpecies(name="Cuarzo")
        current_locality = Locality(
            name="Colmenarejo",
            region="Madrid",
            country="España",
        )
        other_locality = Locality(
            name="Mina Test",
            region="Asturias",
            country="España",
        )
        item = CollectionItem(
            item_code="MIN-0001",
            mineral=mineral,
            locality=current_locality,
            sold=False,
        )
        db.add_all([item, other_locality])
        db.commit()
        locality_ids = current_locality.id, other_locality.id

    return engine, test_session, locality_ids


def run_admin_page(*, editing_item_code: str | None = None) -> AppTest:
    app = AppTest.from_file(PAGE_PATH, default_timeout=10)
    app.session_state["admin_unlocked"] = True
    if editing_item_code:
        app.session_state["editing_item_code"] = editing_item_code
    else:
        app.session_state["editing_item_code"] = None
    app.run(timeout=10)
    assert len(app.exception) == 0
    return app


def widget_with_label(widgets, label: str):
    return next(widget for widget in widgets if widget.label == label)


def test_add_form_can_select_an_existing_or_create_a_new_locality(monkeypatch, tmp_path):
    engine, test_session, (_, other_locality_id) = prepare_database(monkeypatch, tmp_path)
    try:
        app = run_admin_page()
        locality_select = widget_with_label(app.selectbox, "Localidad")

        assert locality_select.value == NEW_LOCALITY_OPTION
        assert "País" in [widget.label for widget in app.text_input]

        locality_select.set_value(locality_option(other_locality_id)).run(timeout=10)

        assert len(app.exception) == 0
        assert "País" not in [widget.label for widget in app.text_input]
        assert any("Mina Test" in message.value for message in app.info)

        widget_with_label(app.button, "Guardar pieza").click().run(timeout=10)
        assert len(app.exception) == 0

        with test_session() as db:
            created = db.scalar(
                select(CollectionItem).where(CollectionItem.item_code == "MIN-0002")
            )
            assert created is not None
            assert created.locality_id == other_locality_id
            assert db.scalar(select(func.count(Locality.id))) == 2

        new_app = run_admin_page()
        widget_with_label(new_app.text_input, "País").input("Portugal")
        widget_with_label(new_app.text_input, "Nombre localidad").input("Sintra")
        widget_with_label(new_app.button, "Guardar pieza").click().run(timeout=10)
        assert len(new_app.exception) == 0

        with test_session() as db:
            created = db.scalar(
                select(CollectionItem).where(CollectionItem.item_code == "MIN-0003")
            )
            assert created is not None
            assert created.locality is not None
            assert created.locality.name == "Sintra"
            assert created.locality.country == "Portugal"
    finally:
        engine.dispose()


def test_edit_form_defaults_to_current_locality_and_can_change_or_clear_it(monkeypatch, tmp_path):
    engine, test_session, (current_locality_id, other_locality_id) = prepare_database(
        monkeypatch,
        tmp_path,
    )
    try:
        app = run_admin_page(editing_item_code="MIN-0001")
        locality_select = widget_with_label(app.selectbox, "Localidad")

        assert widget_with_label(app.radio, "Modo").value == "Editar existente"
        assert locality_select.value == locality_option(current_locality_id)

        locality_select.set_value(locality_option(other_locality_id)).run(timeout=10)
        widget_with_label(app.button, "Guardar cambios").click().run(timeout=10)
        assert len(app.exception) == 0

        with test_session() as db:
            item = db.scalar(
                select(CollectionItem).where(CollectionItem.item_code == "MIN-0001")
            )
            original_locality = db.get(Locality, current_locality_id)
            assert item is not None
            assert item.locality_id == other_locality_id
            assert original_locality is not None
            assert original_locality.name == "Colmenarejo"
            assert db.scalar(select(func.count(Locality.id))) == 2

        clear_app = run_admin_page(editing_item_code="MIN-0001")
        widget_with_label(clear_app.selectbox, "Localidad").set_value(
            NO_LOCALITY_OPTION
        ).run(timeout=10)
        assert widget_with_label(clear_app.selectbox, "Localidad").value == NO_LOCALITY_OPTION
        widget_with_label(clear_app.button, "Guardar cambios").click().run(timeout=10)
        assert len(clear_app.exception) == 0

        with test_session() as db:
            item = db.scalar(
                select(CollectionItem).where(CollectionItem.item_code == "MIN-0001")
            )
            assert item is not None
            assert item.locality_id is None
    finally:
        engine.dispose()


def test_edit_form_can_create_a_new_locality_and_selects_it_after_save(monkeypatch, tmp_path):
    engine, test_session, _ = prepare_database(monkeypatch, tmp_path)
    try:
        app = run_admin_page(editing_item_code="MIN-0001")
        widget_with_label(app.selectbox, "Localidad").set_value(
            NEW_LOCALITY_OPTION
        ).run(timeout=10)

        widget_with_label(app.text_input, "País").input("Portugal")
        widget_with_label(app.text_input, "Nombre localidad").input("Sintra")
        widget_with_label(app.button, "Guardar cambios").click().run(timeout=10)
        assert len(app.exception) == 0

        with test_session() as db:
            item = db.scalar(
                select(CollectionItem).where(CollectionItem.item_code == "MIN-0001")
            )
            assert item is not None
            assert item.locality is not None
            assert item.locality.name == "Sintra"
            assert item.locality.country == "Portugal"
            saved_locality_id = item.locality_id
            assert saved_locality_id is not None

        assert widget_with_label(app.selectbox, "Localidad").value == locality_option(
            saved_locality_id
        )
        assert any("Pieza MIN-0001 actualizada" in message.value for message in app.success)
    finally:
        engine.dispose()
