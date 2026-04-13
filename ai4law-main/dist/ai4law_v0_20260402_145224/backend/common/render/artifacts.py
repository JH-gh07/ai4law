from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


def render_pdf_report(output_path: Path, title: str, sections: list[tuple[str, str]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    margin = 40
    y = height - margin

    font_name = "Helvetica"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:  # noqa: BLE001
        font_name = "Helvetica"

    pdf.setTitle(title)
    pdf.setFont(font_name, 15)
    pdf.drawString(margin, y, title)
    y -= 28

    for header, content in sections:
        if y < margin + 40:
            pdf.showPage()
            pdf.setFont(font_name, 12)
            y = height - margin
        pdf.setFont(font_name, 12)
        pdf.drawString(margin, y, header)
        y -= 18

        pdf.setFont(font_name, 10)
        for line in _wrap_lines(content or "", max_chars=70):
            if y < margin + 20:
                pdf.showPage()
                pdf.setFont(font_name, 10)
                y = height - margin
            pdf.drawString(margin + 8, y, line)
            y -= 14
        y -= 8

    pdf.save()
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


def _wrap_lines(text: str, max_chars: int = 70) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        raw = raw.strip()
        if not raw:
            lines.append("")
            continue
        while len(raw) > max_chars:
            lines.append(raw[:max_chars])
            raw = raw[max_chars:]
        lines.append(raw)
    return lines

