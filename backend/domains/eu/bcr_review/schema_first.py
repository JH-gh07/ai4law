"""Schema-first BCR adapter — v4 DocumentIR built from *structured* results.

T02 rewires the BCR adapter so it no longer reverse-engineers layout from
``BCRChapter.content`` Markdown. The authoritative input is the structured
``BCRFinding[]`` + ``BCRTypeClassification`` + rating/score + missing
requirements + citation registry, exactly as produced by the document-driven
review pipeline. Each finding becomes one ``FindingRecord`` with exactly one
``FINDING_DETAIL`` display; summaries only reference findings; citations keep
their stable ID (no ``[N]`` written into block text); and a suggested revision
is structured as a ``ClauseNode`` before it reaches the renderer.

The legacy chapter-based reader is retained only as a deprecated shim
(``build_bcr_document_ir_from_chapters``) for the form-driven path, which T07
exits. It must never feed the document-driven renderer.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
from backend.common.reporting import (
    ActionRecord,
    CitationNoteBlock,
    ClauseGroupBlock,
    ClauseNode,
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    FindingSummaryBlock,
    KeyValueBlock,
    KeyValueItem,
    ListBlock,
    ListItem,
    ParagraphBlock,
    SectionIR,
    legacy_registry_to_reporting,
)
from backend.common.reporting.schema import Identity, Lifecycle, Provenance, ReportMetadata
from backend.common.reporting.schema.citations import CitationRegistry
from backend.domains.eu.bcr_review.schema import BCRChapter, BCRFinding, BCRTypeClassification

_FOOTNOTE_RE = re.compile(r"\[\d+\]")
_NUMBERED_LINE_RE = re.compile(r"^\s*(?:(\d+)\s*[.、)]|\(([a-z])\))\s*(.+?)\s*$")

# Deterministic IR section/block id space (single authoritative numbering).
_SECTIONS = (
    ("bcr.s1", "报告摘要"),
    ("bcr.s2", "BCR 类型与审查范围"),
    ("bcr.s3", "风险与 finding 摘要"),
    ("bcr.s4", "详细 finding"),
    ("bcr.s5", "整改优先级"),
    ("bcr.s6", "建议条款"),
    ("bcr.s7", "法规与引用"),
    ("bcr.s8", "审查边界"),
)


def _clean_legal_basis(labels: list[str]) -> list[str]:
    cleaned: list[str] = []
    for label in labels:
        value = _FOOTNOTE_RE.sub("", label or "").strip()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _resolve_citation_refs(finding: BCFinding, registry: LegacyCitationRegistry) -> list[str]:  # noqa: F821 - ruff false positive; BCRFinding is imported above
    refs: list[str] = []
    for citation_id in getattr(finding, "citation_refs", []) or []:
        if citation_id and citation_id not in refs:
            refs.append(citation_id)
    footnote_map = registry.get_footnote_map() if registry is not None else {}
    for label in finding.legal_basis:
        for match in _FOOTNOTE_RE.finditer(label or ""):
            item = footnote_map.get(int(match.group(1)))
            if item is not None and item.citation_id not in refs:
                refs.append(item.citation_id)
    return refs


def _finding_status(risk_level: str) -> str:
    return "OPEN_BLOCKING" if risk_level == "HIGH" else "OPEN"


def _finding_record(finding: BCFinding, index: int, registry: LegacyCitationRegistry) -> FindingRecord:  # noqa: F821 - ruff false positive; BCRFinding is imported above
    statement = (finding.finding or "").strip() or finding.title or finding.requirement_id or "未描述"
    return FindingRecord(
        finding_id=finding.finding_id,
        requirement_id=finding.requirement_id,
        title=finding.title,
        risk_level=finding.risk_level,
        risk_score=finding.risk_score,
        statement=statement,
        legal_basis=_clean_legal_basis(finding.legal_basis),
        recommendation=finding.recommendation,
        suggested_revision=finding.suggested_revision,
        facts_uncertain=finding.facts_uncertain,
        review_confidence=finding.review_confidence,
        citation_refs=_resolve_citation_refs(finding, registry),
        status=_finding_status(finding.risk_level),
    )


def _clause_node(finding: BCRFinding, index: int) -> ClauseNode:
    """Structure one suggested_revision into a stable, numbered ClauseNode.

    A single-paragraph suggestion becomes one node. A suggestion already split
    into numbered lines becomes a parent node with ``lower_alpha`` children —
    numbering stays in the schema, never hand-written into the text.
    """
    node_id = f"clause.{finding.finding_id}"
    label = f"{finding.requirement_id} {finding.title}".strip()
    text = (finding.suggested_revision or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if len(lines) >= 2 and all(_NUMBERED_LINE_RE.match(line) for line in lines):
        children = [
            ClauseNode(
                node_id=f"{node_id}.{idx}",
                text=_NUMBERED_LINE_RE.match(line).group(3).strip(),
                numbering_style=(
                    "lower_alpha" if _NUMBERED_LINE_RE.match(line).group(2) else "decimal"
                ),
            )
            for idx, line in enumerate(lines, 1)
        ]
        return ClauseNode(node_id=node_id, label=label, text=label or f"建议条款 {index}", children=children)

    return ClauseNode(node_id=node_id, label=label or None, text=text or label or f"建议条款 {index}")


def build_bcr_document_ir(
    *,
    task_id: str,
    company_name: str,
    type_class: BCRTypeClassification,
    rating: str,
    score: float,
    findings: list[BCRFinding],
    missing: list[str],
    citation_registry: LegacyCitationRegistry,
    metadata: dict,
    model: str,
    generated_at: datetime | None = None,
) -> tuple[DocumentIR, CitationRegistry]:
    """Build v4 DocumentIR from structured BCR results (authoritative path)."""
    reporting_registry = legacy_registry_to_reporting(citation_registry)
    timestamp = generated_at or datetime.now(timezone.utc)

    finding_records = [
        _finding_record(finding, index, citation_registry)
        for index, finding in enumerate(findings, start=1)
    ]

    # ── section 3: finding summary (references only, no duplicated body) ──
    summary_blocks: list = []
    if finding_records:
        summary_blocks.append(
            FindingSummaryBlock(
                block_id="bcr.s3.summary",
                finding_refs=[f.finding_id for f in finding_records],
            )
        )

    # ── section 4: one primary display per finding ──
    detail_blocks = [
        FindingDetailBlock(block_id=f"bcr.s4.detail.{f.finding_id}", finding_ref=f.finding_id)
        for f in finding_records
    ]

    # ── section 5: remediation priority ──
    high = [f for f in finding_records if f.risk_level == "HIGH"]
    medium = [f for f in finding_records if f.risk_level == "MEDIUM"]
    low = [f for f in finding_records if f.risk_level == "LOW"]
    priority_items = [
        ListItem(text=f"高风险项（立即整改）：{len(high)} 项"),
        ListItem(text=f"中风险项（建议整改）：{len(medium)} 项"),
        ListItem(text=f"低风险项（跟踪观察）：{len(low)} 项"),
    ]

    # ── section 6: suggested clauses ──
    clause_nodes = [
        _clause_node(finding, index)
        for index, finding in enumerate(findings, start=1)
        if (finding.suggested_revision or "").strip()
    ]

    # ── actions: one remediation action per finding (P0 for HIGH, else P1) ──
    action_records = [
        ActionRecord(
            action_id=f"action.{f.finding_id}",
            finding_refs=[f.finding_id],
            title=f"整改：{f.title}",
            priority="P0" if f.risk_level == "HIGH" else "P1",
        )
        for f in finding_records
    ]

    # ── section 7: citations (stable IDs, appendix generated by renderer) ──
    all_citation_refs: list[str] = []
    for f in finding_records:
        for citation_id in f.citation_refs:
            if citation_id not in all_citation_refs:
                all_citation_refs.append(citation_id)
    citation_blocks: list = []
    if all_citation_refs:
        citation_blocks.append(
            CitationNoteBlock(block_id="bcr.s7.citations", citation_refs=all_citation_refs)
        )

    sections = [
        SectionIR(
            section_id="bcr.s1",
            title="报告摘要",
            level=1,
            ordinal="1",
            blocks=[
                KeyValueBlock(
                    block_id="bcr.s1.summary",
                    items=[
                        KeyValueItem(label="BCR 类型", value=type_class.actual_bcr_type),
                        KeyValueItem(label="类型一致性", value=type_class.type_consistency),
                        KeyValueItem(label="综合评级", value=f"{rating} ({score}/100)"),
                        KeyValueItem(label="发现问题", value=f"{len(findings)} 项"),
                        KeyValueItem(label="缺失强制项", value=f"{len(missing)} 项"),
                    ],
                ),
            ],
        ),
        SectionIR(
            section_id="bcr.s2",
            title="BCR 类型与审查范围",
            level=1,
            ordinal="2",
            blocks=[
                KeyValueBlock(
                    block_id="bcr.s2.type",
                    items=[
                        KeyValueItem(label="声明类型", value=type_class.declared_bcr_type),
                        KeyValueItem(label="检测类型", value=type_class.actual_bcr_type),
                        KeyValueItem(label="一致性", value=type_class.type_consistency),
                        KeyValueItem(label="风险等级", value=type_class.risk_level),
                    ],
                ),
            ]
            + ([ParagraphBlock(block_id="bcr.s2.recommendation", text=type_class.recommendation)]
               if type_class.recommendation else [])
            + ([ListBlock(
                    block_id="bcr.s2.missing",
                    ordered=True,
                    items=[ListItem(text=item) for item in missing],
                )]
               if missing else []),
        ),
        SectionIR(
            section_id="bcr.s3",
            title="风险与 finding 摘要",
            level=1,
            ordinal="3",
            blocks=summary_blocks,
        ),
        SectionIR(
            section_id="bcr.s4",
            title="详细 finding",
            level=1,
            ordinal="4",
            blocks=detail_blocks,
        ),
        SectionIR(
            section_id="bcr.s5",
            title="整改优先级",
            level=1,
            ordinal="5",
            blocks=[
                ListBlock(block_id="bcr.s5.priority", ordered=False, items=priority_items),
            ],
        ),
        SectionIR(
            section_id="bcr.s6",
            title="建议条款",
            level=1,
            ordinal="6",
            blocks=(
                [ClauseGroupBlock(block_id="bcr.s6.clauses", title="建议条款", clauses=clause_nodes)]
                if clause_nodes
                else [ParagraphBlock(block_id="bcr.s6.empty", text="无需修改的条款。")]
            ),
        ),
        SectionIR(
            section_id="bcr.s7",
            title="法规与引用",
            level=1,
            ordinal="7",
            blocks=citation_blocks or [
                ParagraphBlock(block_id="bcr.s7.empty", text="未检索到法规依据。")
            ],
        ),
        SectionIR(
            section_id="bcr.s8",
            title="审查边界",
            level=1,
            ordinal="8",
            blocks=[
                ParagraphBlock(
                    block_id="bcr.s8.boundary",
                    text="本报告由自动化 BCR 审查系统生成，仅供参考，不构成正式法律意见。审查范围限于已上传 BCR 文档的文本内容。",
                ),
            ],
        ),
    ]

    document = DocumentIR(
        document_id=f"bcr:{task_id}",
        report_type="bcr",
        identity=Identity(document_id=f"bcr:{task_id}", report_id=task_id, module_key="bcr"),
        lifecycle=Lifecycle(created_at=timestamp, state="DRAFT", report_status="DRAFT"),
        findings=finding_records,
        actions=action_records,
        citations=list(reporting_registry.records().values()),
        metadata=ReportMetadata(
            title=f"{company_name} — BCR 合规审查报告草案",
            company_name=company_name,
            jurisdiction="EU",
            report_date=timestamp.date().isoformat(),
            report_id=task_id,
        ),
        sections=sections,
        provenance=Provenance(generated_at=timestamp),
        compiler_version="0.1.0",
        prompt_version="bcr-structured-v4",
        template_version="bcr-v0",
        model=model,
    )
    return document, reporting_registry


# ---------------------------------------------------------------------------
# Deprecated legacy reader (form-driven path only). T07 removes this path.
# ---------------------------------------------------------------------------

def build_bcr_document_ir_from_chapters(
    *,
    task_id: str,
    company_name: str,
    chapters: list[BCRChapter],
    citation_registry: LegacyCitationRegistry,
    model: str,
    generated_at: datetime | None = None,
) -> tuple[DocumentIR, CitationRegistry]:
    """Legacy chapter-content reader. Do NOT feed the document-driven renderer."""
    from backend.common.llm.postprocess import strip_markdown_inline
    from backend.common.reporting import ClaimBlock, extract_citation_refs

    reporting_registry = legacy_registry_to_reporting(citation_registry)
    sections: list[SectionIR] = []
    for chapter in chapters:
        blocks = []
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", chapter.content) if part.strip()]
        for index, paragraph in enumerate(paragraphs, start=1):
            citation_free, citation_refs = extract_citation_refs(paragraph, citation_registry)
            residue = _FOOTNOTE_RE.findall(citation_free)
            if residue:
                citation_refs = list(dict.fromkeys(citation_refs + residue))
                citation_free = _FOOTNOTE_RE.sub("", citation_free)
            text = strip_markdown_inline(citation_free).strip()
            if not text:
                continue
            block_id = f"bcr.chapter.{chapter.chapter_no}.block.{index}"
            if citation_refs:
                blocks.append(ClaimBlock(
                    block_id=block_id,
                    text=text,
                    citation_refs=citation_refs,
                    verification="verified" if all(reporting_registry.resolve(r) is not None for r in citation_refs) else "missing_evidence",
                ))
            else:
                blocks.append(ParagraphBlock(block_id=block_id, text=text))
        sections.append(SectionIR(
            section_id=f"bcr.chapter.{chapter.chapter_no}",
            title=chapter.title,
            level=2,
            ordinal=str(chapter.chapter_no),
            blocks=blocks,
        ))

    timestamp = generated_at or datetime.now(timezone.utc)
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="legacy-bcr-adapter-v1",
        template_version="bcr-v0",
        model=model,
        document_id=f"bcr:{task_id}",
        report_type="bcr",
        metadata=ReportMetadata(
            title=f"{company_name} — BCR 合规审查报告草案",
            company_name=company_name,
            report_date=timestamp.date().isoformat(),
            report_id=task_id,
        ),
        sections=sections,
        provenance=Provenance(generated_at=timestamp),
    )
    return document, reporting_registry
