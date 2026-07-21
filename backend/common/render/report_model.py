"""Small, module-neutral report model shared by output renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CitationRef:
    citation_id: str
    source_title: str
    article: str = ""
    snippet: str = ""
    footnote_number: int | None = None


@dataclass
class Paragraph:
    text: str
    citations: list[CitationRef] = field(default_factory=list)


@dataclass
class HeadingBlock:
    text: str
    level: int = 3


@dataclass
class TableBlock:
    headers: list[str]
    rows: list[list[str]]
    caption: str = ""


@dataclass
class ListBlock:
    items: list[str]
    ordered: bool = False


@dataclass
class DividerBlock:
    pass


Block = Paragraph | HeadingBlock | TableBlock | ListBlock | DividerBlock


@dataclass
class Section:
    heading: str
    blocks: list[Block] = field(default_factory=list)
    level: int = 2
    citations: list[CitationRef] = field(default_factory=list)


@dataclass
class ReportMetadata:
    title: str
    company_name: str = ""
    report_date: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d"))
    jurisdiction: str = "cn"
    report_id: str = ""
    module: str = ""
    template_key: str = ""


@dataclass
class ReportDocument:
    metadata: ReportMetadata
    sections: list[Section] = field(default_factory=list)
    citations: list[CitationRef] = field(default_factory=list)

    def add_section(self, heading: str, level: int = 2) -> Section:
        section = Section(heading=heading, level=level)
        self.sections.append(section)
        return section

    def collect_all_citations(self) -> list[CitationRef]:
        refs = list(self.citations)
        refs.extend(ref for section in self.sections for ref in section.citations)
        refs.extend(
            ref
            for section in self.sections
            for block in section.blocks
            if isinstance(block, Paragraph)
            for ref in block.citations
        )
        return list({ref.citation_id: ref for ref in refs}.values())


class ReportBuilder:
    def __init__(
        self,
        title: str,
        company_name: str = "",
        module: str = "",
        jurisdiction: str = "cn",
    ) -> None:
        self._document = ReportDocument(
            ReportMetadata(
                title=title,
                company_name=company_name,
                module=module,
                jurisdiction=jurisdiction,
            )
        )
        self._current_section: Section | None = None

    def add_section(self, heading: str, level: int = 2) -> ReportBuilder:
        self._current_section = self._document.add_section(heading, level)
        return self

    def _section(self) -> Section:
        if self._current_section is None:
            raise ValueError("add_section() must be called before adding report blocks")
        return self._current_section

    def add_heading(self, text: str, level: int = 3) -> ReportBuilder:
        self._section().blocks.append(HeadingBlock(text=text, level=level))
        return self

    def add_paragraph(
        self, text: str, citations: list[CitationRef] | None = None
    ) -> ReportBuilder:
        self._section().blocks.append(Paragraph(text=text, citations=citations or []))
        return self

    def add_table(
        self, headers: list[str], rows: list[list[str]], caption: str = ""
    ) -> ReportBuilder:
        self._section().blocks.append(TableBlock(headers=headers, rows=rows, caption=caption))
        return self

    def add_list(self, items: list[str], ordered: bool = False) -> ReportBuilder:
        self._section().blocks.append(ListBlock(items=items, ordered=ordered))
        return self

    def add_divider(self) -> ReportBuilder:
        self._section().blocks.append(DividerBlock())
        return self

    def build(self) -> ReportDocument:
        return self._document
