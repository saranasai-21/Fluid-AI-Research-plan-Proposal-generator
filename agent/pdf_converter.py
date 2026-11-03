"""
PDF Converter Service for Fluid AI.
Converts .docx documents to .pdf with a robust multi-strategy fallback:
1. Windows Microsoft Word COM / docx2pdf (Native high-fidelity fidelity)
2. ReportLab parsing fallback (Pure Python, headless, no Word dependency needed)
"""

from __future__ import annotations
import logging
from pathlib import Path
import docx
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger("fluid_ai.pdf")


def convert_docx_to_pdf_reportlab(docx_path: Path, pdf_path: Path) -> Path:
    """Fallback generator converting .docx content into a styled ReportLab PDF."""
    doc = docx.Document(str(docx_path))
    pdf_doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocxTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=15,
    )
    h1_style = ParagraphStyle(
        "DocxH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "DocxH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "DocxBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )
    bullet_style = ParagraphStyle(
        "DocxBullet",
        parent=body_style,
        leftIndent=16,
        bulletIndent=6,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "DocxCell",
        parent=body_style,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=0,
    )
    cell_head_style = ParagraphStyle(
        "DocxCellHead",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=0,
    )

    story = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            story.append(Spacer(1, 6))
            continue

        clean_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        p_style_name = para.style.name.lower() if para.style else ""

        if "title" in p_style_name:
            story.append(Paragraph(clean_text, title_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6366f1"), spaceAfter=15))
        elif "heading 1" in p_style_name:
            story.append(Paragraph(clean_text, h1_style))
        elif "heading 2" in p_style_name:
            story.append(Paragraph(clean_text, h2_style))
        elif "list" in p_style_name or clean_text.startswith(("-", "•", "*")):
            bullet_clean = clean_text.lstrip("-•* ")
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{bullet_clean}", bullet_style))
        else:
            story.append(Paragraph(clean_text, body_style))

    # Process tables
    for table in doc.tables:
        table_data = []
        for row_idx, row in enumerate(table.rows):
            row_data = []
            for cell in row.cells:
                cell_text = cell.text.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                st = cell_head_style if row_idx == 0 else cell_style
                row_data.append(Paragraph(cell_text, st))
            if row_data:
                table_data.append(row_data)

        if table_data:
            t = Table(table_data, colWidths=None, repeatRows=1)
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            story.append(Spacer(1, 8))
            story.append(t)
            story.append(Spacer(1, 10))

    pdf_doc.build(story)
    return pdf_path


def convert_docx_to_pdf(docx_path: Path) -> Path:
    """
    Converts docx file to pdf, caching the output alongside the docx file.
    Uses docx2pdf (Word COM) first, falls back to ReportLab.
    """
    docx_path = Path(docx_path).resolve()
    pdf_path = docx_path.with_suffix(".pdf")

    # If PDF already generated and newer than docx, return cached
    if pdf_path.exists() and pdf_path.stat().st_mtime >= docx_path.stat().st_mtime:
        return pdf_path

    logger.info(f"Converting {docx_path.name} to PDF...")

    # Method 1: docx2pdf (Native Windows Word COM automation)
    try:
        from docx2pdf import convert
        import pythoncom
        pythoncom.CoInitialize()
        try:
            convert(str(docx_path), str(pdf_path))
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                logger.info(f"Successfully converted using docx2pdf: {pdf_path.name}")
                return pdf_path
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        logger.warning(f"docx2pdf failed or Word not running ({e}). Falling back to ReportLab...")

    # Method 2: Pure Python ReportLab fallback
    try:
        convert_docx_to_pdf_reportlab(docx_path, pdf_path)
        logger.info(f"Successfully generated PDF using ReportLab: {pdf_path.name}")
        return pdf_path
    except Exception as e:
        logger.error(f"ReportLab conversion also failed: {e}")
        raise RuntimeError(f"Could not convert document to PDF: {e}")

