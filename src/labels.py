from __future__ import annotations

import html
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from textwrap import dedent

import reportlab
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


LABEL_WIDTH = 30 * mm
LABEL_HEIGHT = 15 * mm
LABELS_PER_ROW = 6
LABELS_PER_COLUMN = 18
LABELS_PER_PAGE = LABELS_PER_ROW * LABELS_PER_COLUMN
LABEL_HORIZONTAL_PADDING = 1.2 * mm

_CODE_NUMBER_RE = re.compile(r"(\d+)$")
_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONTS_READY = False


@dataclass(frozen=True)
class MineralLabel:
    name: str
    identifier: str
    locality: str

    @property
    def title(self) -> str:
        return f"{self.name}  {self.identifier}".strip()


def label_identifier(item_code: str | None, database_id: int | None = None) -> str:
    """Return the compact, four-digit collection identifier used on labels."""
    clean_code = str(item_code or "").strip()
    match = _CODE_NUMBER_RE.search(clean_code)
    if match:
        number = match.group(1)
        return number.zfill(max(4, len(number)))
    if database_id is not None:
        return str(database_id).zfill(4)
    return clean_code or "----"


def locality_text(locality: object | None) -> str:
    """Build the label locality, preferring region over locality name."""
    if locality is None:
        return "Procedencia desconocida"

    parts: list[str] = []
    seen: set[str] = set()
    mine = str(getattr(locality, "mine", "") or "").strip()
    locality_name = str(getattr(locality, "name", "") or "").strip()
    place = mine or locality_name
    for value in (
        place,
        getattr(locality, "region", ""),
        getattr(locality, "country", ""),
    ):
        value = str(value or "").strip()
        key = " ".join(value.casefold().split())
        if value and key not in seen:
            parts.append(value)
            seen.add(key)
    return " › ".join(parts) if parts else "Procedencia desconocida"


def mineral_label_from_item(item: object) -> MineralLabel:
    mineral = getattr(item, "mineral", None)
    mineral_name = str(getattr(mineral, "name", "") or "").strip()
    display_name = str(getattr(item, "display_name", "") or "").strip()
    return MineralLabel(
        name=display_name or mineral_name or "Sin nombre",
        identifier=label_identifier(
            getattr(item, "item_code", None),
            getattr(item, "id", None),
        ),
        locality=locality_text(getattr(item, "locality", None)),
    )


def _register_unicode_fonts() -> tuple[str, str]:
    global _FONTS_READY, _FONT_REGULAR, _FONT_BOLD
    if _FONTS_READY:
        return _FONT_REGULAR, _FONT_BOLD

    candidates = [
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ),
        (
            Path(reportlab.__file__).resolve().parent / "fonts" / "Vera.ttf",
            Path(reportlab.__file__).resolve().parent / "fonts" / "VeraBd.ttf",
        ),
    ]
    for regular_path, bold_path in candidates:
        if regular_path.exists() and bold_path.exists():
            try:
                pdfmetrics.registerFont(TTFont("MineralLabelSans", str(regular_path)))
                pdfmetrics.registerFont(TTFont("MineralLabelSansBold", str(bold_path)))
            except Exception:
                continue
            _FONT_REGULAR = "MineralLabelSans"
            _FONT_BOLD = "MineralLabelSansBold"
            break

    _FONTS_READY = True
    return _FONT_REGULAR, _FONT_BOLD


def fitted_font_size(
    text: str,
    font_name: str,
    max_width: float,
    max_font_size: float,
) -> float:
    """Return a font size that keeps the full line inside the available width."""
    width_at_one_point = pdfmetrics.stringWidth(text, font_name, 1)
    if width_at_one_point <= 0:
        return max_font_size
    return max(min(max_font_size, max_width / width_at_one_point), 0.1)


def _draw_label(pdf: canvas.Canvas, label: MineralLabel, x: float, y: float) -> None:
    regular_font, bold_font = _register_unicode_fonts()
    text_width = LABEL_WIDTH - (2 * LABEL_HORIZONTAL_PADDING)
    title_size = fitted_font_size(label.title, bold_font, text_width, 7.2)
    locality_size = fitted_font_size(label.locality, regular_font, text_width, 5.4)

    pdf.setStrokeColor(HexColor("#777777"))
    pdf.setLineWidth(0.25)
    pdf.rect(x, y, LABEL_WIDTH, LABEL_HEIGHT, stroke=1, fill=0)
    pdf.setStrokeColor(HexColor("#d2d2d2"))
    pdf.line(
        x + LABEL_HORIZONTAL_PADDING,
        y + 7.2 * mm,
        x + LABEL_WIDTH - LABEL_HORIZONTAL_PADDING,
        y + 7.2 * mm,
    )

    pdf.setFillColor(HexColor("#111111"))
    pdf.setFont(bold_font, title_size)
    pdf.drawCentredString(x + (LABEL_WIDTH / 2), y + 9.4 * mm, label.title)
    pdf.setFillColor(HexColor("#333333"))
    pdf.setFont(regular_font, locality_size)
    pdf.drawCentredString(x + (LABEL_WIDTH / 2), y + 3.4 * mm, label.locality)


def generate_labels_pdf(labels: list[MineralLabel]) -> bytes:
    """Lay out exact 30 x 15 mm labels on centered A4 sheets."""
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4, pageCompression=1)
    pdf.setTitle("Etiquetas de la colección de minerales")
    page_width, page_height = A4
    grid_width = LABELS_PER_ROW * LABEL_WIDTH
    grid_height = LABELS_PER_COLUMN * LABEL_HEIGHT
    margin_x = (page_width - grid_width) / 2
    margin_y = (page_height - grid_height) / 2

    for index, label in enumerate(labels):
        page_position = index % LABELS_PER_PAGE
        if index and page_position == 0:
            pdf.showPage()
        column = page_position % LABELS_PER_ROW
        row = page_position // LABELS_PER_ROW
        x = margin_x + (column * LABEL_WIDTH)
        y = page_height - margin_y - ((row + 1) * LABEL_HEIGHT)
        _draw_label(pdf, label, x, y)

    pdf.save()
    return output.getvalue()


def labels_preview_html(labels: list[MineralLabel]) -> str:
    """Return an enlarged two-row preview that mirrors the generated labels."""
    regular_font, bold_font = _register_unicode_fonts()
    max_width = LABEL_WIDTH - (2 * LABEL_HORIZONTAL_PADDING)
    cards = []
    for label in labels:
        title_size = fitted_font_size(label.title, bold_font, max_width, 7.2) * 1.85
        locality_size = (
            fitted_font_size(label.locality, regular_font, max_width, 5.4) * 1.85
        )
        cards.append(
            dedent(
                """
            <div class="mineral-label-preview">
              <div class="mineral-label-title" style="font-size:{title_size:.2f}pt">{title}</div>
              <div class="mineral-label-locality" style="font-size:{locality_size:.2f}pt">{locality}</div>
            </div>
                """
            ).strip().format(
                    title_size=title_size,
                    locality_size=locality_size,
                    title=html.escape(label.title),
                    locality=html.escape(label.locality),
                )
        )

    template = dedent(
        """
    <style>
      .mineral-label-sheet {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        max-height: 470px;
        overflow-y: auto;
        padding: 12px;
        border: 1px solid #c4a882;
        border-radius: 8px;
        background: #ede8de;
      }
      .mineral-label-preview {
        box-sizing: border-box;
        width: 60mm;
        height: 30mm;
        flex: 0 0 60mm;
        display: grid;
        grid-template-rows: 1fr 1fr;
        align-items: stretch;
        overflow: hidden;
        border: 1px solid #777;
        background: white;
        color: #111;
        font-family: Arial, "DejaVu Sans", sans-serif;
      }
      .mineral-label-title,
      .mineral-label-locality {
        min-width: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        padding: 0 2.4mm;
        overflow: hidden;
        white-space: nowrap;
        line-height: 1;
      }
      .mineral-label-title {
        border-bottom: 1px solid #d2d2d2;
        font-weight: 700;
      }
    </style>
    <div class="mineral-label-sheet">{cards}</div>
        """
    ).strip()
    return template.replace("{cards}", "".join(cards))
