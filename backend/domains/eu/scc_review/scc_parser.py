"""EU SCC document parser — extracts structured SCC from raw text.

Uses regex + heuristics to identify:
- Module Type (One/Two/Three/Four)
- Clauses 1-18
- Annex I.A, I.B, II, III
- Parties, transfer descriptions, TOMs, sub-processors
"""

from __future__ import annotations

import re

from backend.domains.eu.scc_review.schema import (
    SCCAnnexIA,
    SCCAnnexIB,
    SCCAnnexII,
    SCCAnnexIII,
    SCCClause,
    SCCDocument,
    SCCParty,
    SCCTransferChain,
)

_ANNEX_PATTERNS: dict[str, list[str]] = {
    "annex_ia": [
        "ANNEX I", "Annex I", "annex i", "Annex IA", "ANNEX IA",
        "Annex I\\.A", "Annex I-A", "List of Parties",
        "A\\.\\s*LIST OF PARTIES", "ANNEX I\\s*[–\\-]\\s*LIST OF PARTIES",
    ],
    "annex_ib": [
        "Annex I\\.B", "ANNEX I\\.B", "Annex I-B", "ANNEX I-B",
        "Annex IB", "DESCRIPTION OF TRANSFER",
        "B\\.\\s*DESCRIPTION OF(?: THE)? TRANSFER",
        "DESCRIPTION OF(?: THE)? TRANSFER",
    ],
    "annex_ii": [
        "ANNEX II", "Annex II", "annex ii",
        "TECHNICAL AND ORGANISATIONAL MEASURES",
        "Technical and Organisational Measures",
    ],
    "annex_iii": [
        "ANNEX III", "Annex III", "annex iii",
        "LIST OF SUB[-\\s]?PROCESSORS",
        "List of sub-processors", "List of Sub[Pp]rocessors",
    ],
}

_MODULE_PATTERNS = [
    (r"MODULE\s*(ONE|1)", "Module One"),
    (r"MODULE\s*(TWO|2)", "Module Two"),
    (r"MODULE\s*(THREE|3)", "Module Three"),
    (r"MODULE\s*(FOUR|4)", "Module Four"),
    (r"Module\s*(One|1)", "Module One"),
    (r"Module\s*(Two|2)", "Module Two"),
    (r"Module\s*(Three|3)", "Module Three"),
    (r"Module\s*(Four|4)", "Module Four"),
]

_PARTY_ROLE_PATTERNS = [
    r"(?:data\s*)?(exporter|data\s*exporter).*?(?:controller|processor)",
    r"(?:data\s*)?(importer|data\s*importer).*?(?:controller|processor)",
    r"(controller|processor).*?(?:exporter|data exporter)",
    r"(controller|processor).*?(?:importer|data importer)",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _find_module_type(text: str) -> str:
    """Extract SCC module type from document text."""
    for pattern, module_name in _MODULE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return module_name
    return ""


def _split_sections(text: str) -> dict[str, str]:
    """Split SCC document into clause and annex sections."""
    sections: dict[str, str] = {"preamble": "", "clauses": "", "annexes": ""}

    # Annex names are also commonly mentioned in scenario descriptions and
    # clause prose.  Only accept line-level headings here; an inline
    # ``Annex I.B`` reference must not cut the contract in half.
    annex_starts: list[tuple[int, str]] = []
    for annex_key, patterns in _ANNEX_PATTERNS.items():
        for pat in patterns:
            heading_pattern = (
                rf"^[ \t]*(?:\*{{1,2}})?[ \t]*(?:{pat})"
                rf"[ \t]*(?:\*{{1,2}})?[ \t]*$"
            )
            m = re.search(heading_pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                annex_starts.append((m.start(), annex_key))
                break

    annex_starts.sort()
    if annex_starts:
        first_annex = annex_starts[0][0]
        sections["clauses"] = text[:first_annex].strip()
        remaining = text[first_annex:]
        for i, (pos, key) in enumerate(annex_starts):
            start = pos - first_annex
            end = annex_starts[i + 1][0] - first_annex if i + 1 < len(annex_starts) else len(remaining)
            sections[key] = remaining[start:end].strip()
    else:
        sections["clauses"] = text

    return sections


def _extract_clauses(clause_text: str) -> list[SCCClause]:
    """Extract individual clauses from the clauses section."""
    clauses: list[SCCClause] = []

    # Clause names and numbers are frequently cited inside other clauses.  A
    # legal section boundary must therefore be a line-level ``Clause N``
    # heading, optionally wrapped in Markdown emphasis.  Matching loose words
    # such as ``purpose`` or ``data subject`` caused inline references to cut a
    # real clause into fragments.
    heading_re = re.compile(
        r"^[ \t]*(?:\*{1,2})?[ \t]*Clause[ \t]+(\d{1,2})\b[^\n]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    clause_splits: list[tuple[int, str, str]] = []
    seen_clause_numbers: set[int] = set()
    for match in heading_re.finditer(clause_text):
        clause_no = int(match.group(1))
        if not 1 <= clause_no <= 18 or clause_no in seen_clause_numbers:
            continue
        seen_clause_numbers.add(clause_no)
        clause_splits.append(
            (match.start(), f"Clause {clause_no}", match.group(0).strip())
        )

    if clause_splits:
        for i, (pos, title, _) in enumerate(clause_splits):
            end_pos = clause_splits[i + 1][0] if i + 1 < len(clause_splits) else len(clause_text)
            content = clause_text[pos:end_pos].strip()
            clause_no_match = re.search(r"[Cc]lause\s+(\d+)", title)
            clause_no = int(clause_no_match.group(1)) if clause_no_match else 0
            clauses.append(SCCClause(clause_no=clause_no, title=title, content=content))
    else:
        # No clause structure found — treat entire text as single block
        pass

    return clauses


def _extract_annex_ia(text: str) -> SCCAnnexIA:
    """Extract Annex I.A — List of Parties."""
    parties: list[SCCParty] = []

    # Look for party blocks
    party_blocks = re.split(r"(?i)(?:data\s*)?exporter\s*[:\-]", text)
    if len(party_blocks) < 2:
        party_blocks = re.split(r"(?i)(?:data\s*)?importer\s*[:\-]", text)

    for block in party_blocks[1:]:
        block = block.strip()[:500]
        party = SCCParty()

        # Extract name
        name_match = re.search(r"(?:name|名称)[:\s]*(.+)", block, re.IGNORECASE)
        if name_match:
            party.name = name_match.group(1).strip()[:200]

        # Extract address
        addr_match = re.search(r"(?:address|地址)[:\s]*(.+)", block, re.IGNORECASE)
        if addr_match:
            party.address = addr_match.group(1).strip()[:300]

        # Check for incomplete info
        if re.search(r"see\s+(?:master\s+service\s+agreement|MSA)", block, re.IGNORECASE):
            party.is_incomplete = True

        parties.append(party)

    return SCCAnnexIA(parties=parties)


def _extract_annex_ib(text: str) -> SCCAnnexIB:
    """Extract Annex I.B — Description of Transfer."""
    ib = SCCAnnexIB(raw_text=text)

    patterns = {
        "data_subjects": [(r"(?:data\s*)?(?:subjects|categories\s*of\s*data\s*subjects)\s*[:\-]\s*(.+)", re.IGNORECASE)],
        "data_categories": [(r"(?:personal\s*)?data\s*(?:categories\s*)?(?:transferred\s*)?\s*[:\-]\s*(.+)", re.IGNORECASE), (r"data\s*categories\s*[:\-]\s*(.+)", re.IGNORECASE), (r"categories\s*of\s*(?:personal\s*)?data\b[:\-]?\s*(.+)", re.IGNORECASE)],
        "processing_purpose": [(r"(?:purpose|purposes?)\s*(?:of\s*(?:the\s*)?transfer|data\s*processing)?\s*[:\-]\s*(.+)", re.IGNORECASE)],
        "retention_period": [(r"(?:retention|period|duration)\s*[:\-]\s*(.+)", re.IGNORECASE)],
        "transfer_frequency": [(r"(?:frequency|transfer\s*frequency)\s*[:\-]\s*(.+)", re.IGNORECASE)],
    }

    for field, pattern_list in patterns.items():
        for pat_tuple in pattern_list:
            if isinstance(pat_tuple, tuple):
                pattern, flags = pat_tuple[0], pat_tuple[1] if len(pat_tuple) > 1 else 0
            else:
                pattern, flags = pat_tuple, 0
            m = re.search(pattern, text, flags)
            if m:
                setattr(ib, field, m.group(1).strip()[:500])
                break

    # Check for special category data
    for m in re.finditer(
        r"(?:special\s*categor(?:y|ies)\s*(?:of\s*)?(?:personal\s*)?data|sensitive\s*data|health\s*data|genetic|biometric|religious|political|ethnic|trade\s*union)",
        text, re.IGNORECASE
    ):
        ib.special_category_data.append(m.group(0))

    # Check for vague descriptions
    if re.search(r"order\s*history\s*data", text, re.IGNORECASE):
        if not any("order" in cat.lower() for cat in ib.special_category_data):
            pass  # Flagged in rule engine

    return ib


def _extract_annex_ii(text: str) -> SCCAnnexII:
    """Extract Annex II — Technical and Organisational Measures."""
    tom_items: list[str] = []
    supp_items: list[str] = []

    # List items
    for m in re.finditer(r"(?:^|\n)\s*[-•*]\s*(.+)", text):
        item = m.group(1).strip()[:300]
        if any(kw in item.lower() for kw in ("encryption", "tls", "aes", "access control", "pseudonymi", "audit", "log", "firewall")):
            tom_items.append(item)
        else:
            tom_items.append(item)

    # Supplementary measures (Schrems II)
    for kw in ("supplement", "additional", "further measure", "schrems", "onward transfer restriction"):
        if kw in text.lower():
            for m in re.finditer(rf"{kw}[^.]*\.", text, re.IGNORECASE):
                supp_items.append(m.group(0).strip())

    return SCCAnnexII(tom_items=tom_items, supplementary_measures=supp_items)


def _extract_annex_iii(text: str) -> SCCAnnexIII:
    """Extract Annex III — List of Sub-Processors."""
    sub_processors: list[dict] = []

    for m in re.finditer(r"(?:^|\n)\s*[-•*]\s*(.+)", text):
        entry = m.group(1).strip()
        sub_proc = {"name": entry[:200]}

        # Try to extract additional info
        loc_match = re.search(r"(?:located|location|country|地址)\s*(?:in|:)?\s*(.+)", entry, re.IGNORECASE)
        if loc_match:
            sub_proc["location"] = loc_match.group(1).strip()[:100]

        sub_processors.append(sub_proc)

    return SCCAnnexIII(sub_processors=sub_processors)



def _build_transfer_chain(
    exporter_role: str, importer_role: str, doc: SCCDocument, request_chain: str = ""
) -> SCCTransferChain:
    """Build transfer chain model from parsed document and request data."""
    exporter_name = ""
    importer_name = ""

    # Extract from Annex I.A parties
    for party in doc.annex_i_a.parties:
        if not party.name:
            continue
        if not exporter_name and any(r in party.role.lower() for r in ("exporter", "data exporter", "controller")) if party.role else False:
            exporter_name = party.name
        elif not importer_name and any(r in party.role.lower() for r in ("importer", "data importer", "processor")) if party.role else False:
            importer_name = party.name

    if not exporter_name and doc.annex_i_a.parties:
        exporter_name = doc.annex_i_a.parties[0].name
    if not importer_name and len(doc.annex_i_a.parties) > 1:
        importer_name = doc.annex_i_a.parties[1].name

    # Sub-processors from Annex III
    sub_processors = [sp.get("name", "") for sp in doc.annex_iii.sub_processors if sp.get("name")]

    # Storage/access locations from Annex III location fields + text scanning
    locations: list[str] = []
    for sp in doc.annex_iii.sub_processors:
        if sp.get("location"):
            locations.append(sp["location"])

    # Scan doc for country mentions
    english_country_mentions = re.findall(
        r"\b(United\s*States|USA?|India|Serbia|China|UK|United\s*Kingdom|"
        r"Japan|South\s*Korea|Singapore|Brazil|Australia)\b",
        doc.raw_text,
        re.IGNORECASE,
    )
    locations.extend([country.strip() for country in english_country_mentions])
    chinese_country_names = {
        "美国": "United States",
        "印度": "India",
        "塞尔维亚": "Serbia",
        "中国": "China",
        "英国": "United Kingdom",
        "日本": "Japan",
        "韩国": "South Korea",
        "新加坡": "Singapore",
        "巴西": "Brazil",
        "澳大利亚": "Australia",
    }
    locations.extend(
        canonical
        for localized, canonical in chinese_country_names.items()
        if localized in doc.raw_text
    )

    return SCCTransferChain(
        exporter_name=exporter_name,
        exporter_role=exporter_role,
        importer_name=importer_name,
        importer_role=importer_role,
        sub_processors=sub_processors,
        onward_transfer_locations=locations[:5],
        storage_locations=locations[:3],
        access_locations=locations[:3],
    )


# ═══════════════════════════════════════════════════════════════════════
# Main parser entry point
# ═══════════════════════════════════════════════════════════════════════

def parse_scc_document(
    text: str,
    declared_module: str = "",
    exporter_role: str = "",
    importer_role: str = "",
) -> SCCDocument:
    """Parse raw SCC document text into structured SCCDocument.

    Uses regex + heuristics. Falls back gracefully when sections are not found.
    """
    # A test/review packet may contain scenario notes before the submitted SCC.
    # Parse legal sections from the contract portion while preserving the full
    # packet as raw_text so country and transfer-context extraction still works.
    contract_text = text
    review_markers = (
        "提交审查的SCC文档全文（关键问题部分节选）：",
        "提交审查的SCC文档全文（关键部分节选）：",
    )
    marker_positions = [
        (text.rfind(marker), marker)
        for marker in review_markers
        if text.rfind(marker) >= 0
    ]
    if marker_positions:
        marker_pos, marker = max(marker_positions, key=lambda item: item[0])
        contract_text = text[marker_pos + len(marker):].lstrip()

    # Module type
    module_type = _find_module_type(text) or declared_module

    # Section splitting
    sections = _split_sections(contract_text)

    # Clause extraction
    clauses = _extract_clauses(sections.get("clauses", contract_text))

    # Annex extraction
    annex_ia = _extract_annex_ia(sections.get("annex_ia", ""))
    annex_ib = _extract_annex_ib(sections.get("annex_ib", ""))
    annex_ii = _extract_annex_ii(sections.get("annex_ii", ""))
    annex_iii = _extract_annex_iii(sections.get("annex_iii", ""))

    return SCCDocument(
        module_type=module_type,
        clauses=clauses,
        annex_i_a=annex_ia,
        annex_i_b=annex_ib,
        annex_ii=annex_ii,
        annex_iii=annex_iii,
        raw_text=text,
    )
