from __future__ import annotations

from html import escape
from pathlib import Path


def render_pdf_from_markdown(markdown_text: str, output_path: Path) -> None:
    try:
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise RuntimeError(
            "reportlab is required for PDF output. Run `uv pip install -e .` first."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "ChineseBase",
        parent=styles["BodyText"],
        fontName="STSong-Light",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    heading = ParagraphStyle(
        "ChineseHeading",
        parent=base,
        fontSize=15,
        leading=20,
        spaceBefore=10,
        spaceAfter=8,
    )
    story = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.2 * cm))
            continue
        style = heading if stripped.startswith("#") else base
        text = stripped.lstrip("#").strip() if stripped.startswith("#") else stripped
        story.append(Paragraph(escape(text), style))

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    document.build(story)
