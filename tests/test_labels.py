import re
from pathlib import Path
from types import SimpleNamespace

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from src import db as db_module
from src.db import Base
from src.labels import (
    LABELS_PER_PAGE,
    LABEL_WIDTH,
    MineralLabel,
    fitted_font_size,
    generate_labels_pdf,
    label_identifier,
    labels_preview_html,
    locality_text,
    mineral_label_from_item,
)
from src.models import CollectionItem, Locality, MineralSpecies


COLLECTION_PAGE_PATH = Path(__file__).resolve().parents[1] / "views" / "1_Coleccion.py"


def test_label_identifier_uses_four_digit_numeric_suffix():
    assert label_identifier("MIN-24", 999) == "0024"
    assert label_identifier("ABC-12345", 999) == "12345"
    assert label_identifier("SIN-CODIGO", 7) == "0007"


def test_locality_text_prefers_region_over_locality_name():
    locality = SimpleNamespace(
        mine="Mina Esperanza",
        name="Almadén",
        region="Castilla-La Mancha",
        country="España",
    )
    assert locality_text(locality) == "Castilla-La Mancha › España"

    locality_fallback = SimpleNamespace(
        mine="Mina Esperanza",
        name="Almadén",
        region=None,
        country="España",
    )
    assert locality_text(locality_fallback) == "Almadén › España"

    country_only = SimpleNamespace(name=None, region=None, country="España")
    assert locality_text(country_only) == "España"


def test_mineral_label_prefers_custom_display_name():
    item = SimpleNamespace(
        id=24,
        item_code="MIN-0024",
        display_name="Cuarzo maestro",
        mineral=SimpleNamespace(name="Cuarzo"),
        locality=None,
    )
    label = mineral_label_from_item(item)
    assert label.title == "Cuarzo maestro  0024"
    assert label.locality == "Procedencia desconocida"


def test_font_size_keeps_long_words_inside_label_width():
    text = "Konstantinovskayaultralargalocalidadsinrecorte"
    available_width = LABEL_WIDTH - (2.4 * mm)
    size = fitted_font_size(text, "Helvetica", available_width, 7.2)
    assert pdfmetrics.stringWidth(text, "Helvetica", size) <= available_width + 0.001


def test_pdf_adds_a_second_page_after_full_a4_sheet():
    labels = [
        MineralLabel(f"Mineral {index}", f"{index:04d}", "España")
        for index in range(LABELS_PER_PAGE + 1)
    ]
    pdf = generate_labels_pdf(labels)

    assert pdf.startswith(b"%PDF-")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 2


def test_preview_escapes_user_supplied_text():
    markup = labels_preview_html([MineralLabel("<script>", "0001", "Mina & país")])
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
    assert "Mina &amp; país" in markup
    assert markup.startswith("<style>")


def test_collection_labels_flow_shows_preview_after_selection(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    test_session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "SessionLocal", test_session)

    with test_session() as db:
        mineral = MineralSpecies(name="Cuarzo")
        locality = Locality(
            mine="Mina Esperanza",
            name="Almadén",
            region="Castilla-La Mancha",
            country="España",
        )
        db.add(
            CollectionItem(
                item_code="MIN-0024",
                display_name="Cuarzo maestro",
                mineral=mineral,
                locality=locality,
                sold=False,
            )
        )
        db.commit()

    try:
        app = AppTest.from_file(COLLECTION_PAGE_PATH, default_timeout=20).run()
        assert not app.exception
        next(button for button in app.button if button.label == "Labels").click().run()
        assert not app.exception

        selector = next(
            widget
            for widget in app.multiselect
            if widget.label == "Minerales para imprimir"
        )
        selector.set_value(["MIN-0024"]).run()

        assert not app.exception
        assert any(
            "Vista previa de 1 etiqueta" in caption.value
            for caption in app.caption
        )
    finally:
        engine.dispose()
