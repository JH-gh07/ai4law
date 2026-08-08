from __future__ import annotations

import re
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_pdf_report(output_path: Path, title: str, sections: list[tuple[str, str]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font_name = _resolve_pdf_font()
    styles = _build_pdf_styles(font_name)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=title,
    )
    story: list = [
        Paragraph(_inline_markup(title), styles["title"]),
        Spacer(1, 14),
    ]

    for header, content in sections:
        story.append(Paragraph(_inline_markup(header), styles["section"]))
        story.append(Spacer(1, 8))
        story.extend(_markdown_to_flowables(content or "", styles, doc.width))
        story.append(Spacer(1, 12))

    doc.build(story)
    return output_path


def render_simple_xlsx(output_path: Path, headers: list[str], rows: list[list[str | int | float]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
""",
        )
        zf.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        )
        zf.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
""",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
""",
        )
        zf.writestr("xl/worksheets/sheet1.xml", _build_sheet_xml(headers, rows))
    return output_path


def bundle_files(output_zip: Path, files: list[Path]) -> Path:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip, mode="w", compression=ZIP_DEFLATED) as zf:
        for file in files:
            if file.exists():
                zf.write(file, arcname=file.name)
    return output_zip


def _build_sheet_xml(headers: list[str], rows: list[list[str | int | float]]) -> str:
    xml_rows: list[str] = []
    all_rows = [headers] + rows
    for ridx, row in enumerate(all_rows, start=1):
        cells: list[str] = []
        for cidx, value in enumerate(row, start=1):
            ref = f"{_excel_col(cidx)}{ridx}"
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{_escape_xml(str(value))}</t></is></c>')
        xml_rows.append(f"<row r=\"{ridx}\">{''.join(cells)}</row>")
    return (
        """<?xml version="1.0" encoding="UTF-8"?>"""
        """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">"""
        f"<sheetData>{''.join(xml_rows)}</sheetData>"
        "</worksheet>"
    )


def _excel_col(index_1_based: int) -> str:
    n = index_1_based
    chars = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        chars.append(chr(ord("A") + rem))
    return "".join(reversed(chars))


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )



def _resolve_pdf_font() -> str:
    font_name = "Helvetica"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:  # noqa: BLE001
        font_name = "Helvetica"
    return font_name


def _build_pdf_styles(font_name: str) -> dict[str, object]:
    from reportlab.lib.styles import ParagraphStyle

    base = ParagraphStyle(
        name="Base",
        fontName=font_name,
        fontSize=10.5,
        leading=16,
        textColor=colors.HexColor("#1f2937"),
    )
    return {
        "title": ParagraphStyle(
            name="Title",
            parent=base,
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            name="Section",
            parent=base,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=2,
            spaceAfter=2,
        ),
        "h1": ParagraphStyle(name="H1", parent=base, fontSize=14, leading=20, spaceBefore=8, spaceAfter=4),
        "h2": ParagraphStyle(name="H2", parent=base, fontSize=12.5, leading=18, spaceBefore=6, spaceAfter=4),
        "h3": ParagraphStyle(name="H3", parent=base, fontSize=11.5, leading=17, spaceBefore=4, spaceAfter=3),
        "p": ParagraphStyle(name="P", parent=base, spaceBefore=2, spaceAfter=3),
        "li": ParagraphStyle(name="LI", parent=base, leftIndent=4, spaceBefore=1, spaceAfter=1),
    }


def _inline_markup(text: str) -> str:
    safe = escape(text or "")
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
    safe = re.sub(r"`([^`]+)`", r"<font color='#0f172a'><b>\1</b></font>", safe)
    return safe


def _markdown_to_flowables(
    content: str,
    styles: dict[str, object],
    available_width: float,
) -> list:
    lines = (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    flowables: list = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line == "---":
            flowables.append(Spacer(1, 6))
            flowables.append(Table([[""]], colWidths=[1], rowHeights=[1], style=TableStyle([
                ("LINEABOVE", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
            ])))
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        if line.startswith("### "):
            flowables.append(Paragraph(_inline_markup(line[4:]), styles["h3"]))
            i += 1
            continue
        if line.startswith("## "):
            flowables.append(Paragraph(_inline_markup(line[3:]), styles["h2"]))
            i += 1
            continue
        if line.startswith("# "):
            flowables.append(Paragraph(_inline_markup(line[2:]), styles["h1"]))
            i += 1
            continue

        ul_match = re.match(r"^-\s+(.+)$", line)
        if ul_match:
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                match = re.match(r"^-\s+(.+)$", cur)
                if not match:
                    break
                items.append(ListItem(Paragraph(_inline_markup(match.group(1)), styles["li"])))
                i += 1
            flowables.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=14))
            continue

        ol_match = re.match(r"^\d+\.\s+(.+)$", line)
        if ol_match:
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                match = re.match(r"^\d+\.\s+(.+)$", cur)
                if not match:
                    break
                items.append(ListItem(Paragraph(_inline_markup(match.group(1)), styles["li"])))
                i += 1
            flowables.append(ListFlowable(items, bulletType="1", leftIndent=14))
            continue

        if "|" in line and line.count("|") >= 2:
            table_lines: list[str] = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur or "|" not in cur or cur.count("|") < 2:
                    break
                table_lines.append(cur)
                i += 1
            flowables.extend(
                _build_table_flowables(table_lines, styles, available_width)
            )
            continue

        flowables.append(Paragraph(_inline_markup(line), styles["p"]))
        i += 1

    return flowables


def _build_table_flowables(
    table_lines: list[str],
    styles: dict[str, object],
    available_width: float,
) -> list:
    if not table_lines:
        return []
    rows = [[cell.strip() for cell in raw.strip("|").split("|")] for raw in table_lines]
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in rows[1]):
        rows.pop(1)
    max_cols = max(len(row) for row in rows)
    normalized = [row + [""] * (max_cols - len(row)) for row in rows]
    cell_data = [
        [Paragraph(_inline_markup(cell), styles["p"]) for cell in row]
        for row in normalized
    ]
    max_lengths = [
        max(len(re.sub(r"<br\s*/?>", " ", row[index], flags=re.IGNORECASE)) for row in normalized)
        for index in range(max_cols)
    ]
    weights = [min(4.0, max(1.0, length / 12)) for length in max_lengths]
    weight_total = sum(weights)
    column_widths = [available_width * weight / weight_total for weight in weights]
    cell_padding = min(6.0, max(1.0, min(column_widths) * 0.15))

    table = Table(cell_data, colWidths=column_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#d0d7de")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5ff")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), cell_padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), cell_padding),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [table, Spacer(1, 6)]
