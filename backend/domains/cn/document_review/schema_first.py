"""Schema-first Review adapter — v4 DocumentIR built from *structured* results.

T02 rewires the review adapter so it no longer wraps ``build_sections`` output
into ParagraphBlocks (I068-02). The authoritative input is the structured
``AggregatedReview``: each ``ReviewIssue`` becomes one ``FindingRecord`` with
exactly one ``FINDING_DETAIL`` display; each ``StructuredCitation`` is attributed
into a ``FindingBasis`` whose ``rationale`` is sourced from ``snippet`` /
``risk_analysis`` (never freshly generated); missing items, actions, scope and
document profile land in typed blocks.

``ReviewReportRenderer.build_sections`` is retained only as a deprecated shim
for the legacy string writers (T05/T06 exit that path). It must never feed the
structured renderer.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
from backend.common.reporting import (
    CitationNoteBlock,
    DocumentIR,
    FindingBasis,
    FindingDetailBlock,
    FindingRecord,
    FindingSummaryBlock,
    KeyValueBlock,
    KeyValueItem,
    ListBlock,
    ListItem,
    ParagraphBlock,
    SectionIR,
    TableBlock,
    WarningBlock,
    legacy_registry_to_reporting,
)
from backend.common.reporting.schema import Identity, Lifecycle, Provenance, ReportMetadata
from backend.common.reporting.schema.citations import CitationLocator, CitationRecord, CitationRegistry
from backend.schemas.review import AggregatedReview, ReviewIssue, StructuredCitation

# Deterministic section id/title space. Unique titles fix the legacy duplicate
# "九" (I068-05) and drop the hand-written Chinese ordinal as identity.
_SECTIONS = (
    ("review.s1", "执行摘要"),
    ("review.s2", "审查概况与方法"),
    ("review.s3", "文档画像"),
    ("review.s4", "整体风险评估"),
    ("review.s5", "完整性检查"),
    ("review.s6", "问题摘要"),
    ("review.s7", "逐条问题"),
    ("review.s8", "优先整改路线图"),
    ("review.s9", "法规依据汇总"),
    ("review.s10", "审查边界与置信度"),
)

_SOURCE_TYPE_MAP = {
    "statute": "regulation",
    "regulation": "regulation",
    "standard": "standard",
    "standard_clause": "standard",
    "guideline": "guide",
    "guide": "guide",
    "case": "case",
    "policy_qa": "policy_qa",
    "user_material": "user_material",
}


def _plain(text: str | None, fallback: str = "") -> str:
    value = (text or "").strip()
    return value or fallback


def _kv(label: str, value: str) -> KeyValueItem:
    return KeyValueItem(label=label, value=_plain(value, "未提供"))


def _finding_status(risk_level: str) -> str:
    return "OPEN_BLOCKING" if risk_level == "HIGH" else "OPEN"


def _citation_label(sc: StructuredCitation) -> str:
    title = _plain(sc.source_title).strip("《》")
    article = _plain(sc.article)
    if title and article:
        return f"《{title}》{article}"
    return title or article or "未命名依据"


def _basis_rationale(issue: ReviewIssue, sc: StructuredCitation) -> str:
    """Attribute rationale from an existing business field only.

    Prefer the citation's own snippet (the excerpt that supports the finding);
    otherwise fall back to the finding-level risk_analysis. Never generate.
    """
    snippet = _plain(sc.snippet)
    if snippet:
        return snippet
    return _plain(issue.risk_analysis)


def _flatten_suggested_revision(issue: ReviewIssue) -> str | None:
    rev = issue.suggested_revision
    if rev is None:
        return None
    parts: list[str] = []
    if _plain(rev.original_text):
        parts.append(f"原文：{_plain(rev.original_text)}")
    if _plain(rev.suggested_text):
        parts.append(f"建议改为：{_plain(rev.suggested_text)}")
    if _plain(rev.revision_rationale):
        parts.append(f"理由：{_plain(rev.revision_rationale)}")
    return "\n".join(parts) or None


def _resolve_structured_citations(
    review: AggregatedReview,
    reporting_registry: CitationRegistry,
) -> tuple[dict[str, list[str]], dict[str, list[FindingBasis]]]:
    """Register structured citations and attribute per-finding basis entries.

    Returns ``(finding_refs, finding_basis)`` keyed by issue_id. Citation IDs are
    deterministic: legacy registry entries are reused by source_id + article when
    they match, otherwise a stable ``CIT-REV-<seq>`` ID is minted in first
    appearance order.
    """
    seen: dict[tuple[str, str, str], str] = {}
    seq = 0
    new_records: list[CitationRecord] = []

    def _existing_citation_id(sc: StructuredCitation) -> str | None:
        norm_article = _plain(sc.article)
        for rec in reporting_registry.records().values():
            if rec.source_id and rec.source_id == sc.source_id:
                rec_article = (rec.locator.article if rec.locator else "") or ""
                if rec_article == norm_article or not norm_article:
                    return rec.citation_id
        return None

    def _resolve(sc: StructuredCitation) -> str:
        nonlocal seq
        key = (_plain(sc.source_id), _plain(sc.source_title), _plain(sc.article))
        existing = seen.get(key)
        if existing:
            return existing
        citation_id = _existing_citation_id(sc)
        if citation_id is None:
            seq += 1
            citation_id = f"CIT-REV-{seq:03d}"
            new_records.append(CitationRecord(
                citation_id=citation_id,
                source_id=_plain(sc.source_id, citation_id),
                source_type=_SOURCE_TYPE_MAP.get(sc.source_type, "regulation"),
                title=_plain(sc.source_title, "未命名依据"),
                locator=CitationLocator(article=_plain(sc.article)) if _plain(sc.article) else None,
                can_enter_external_report=True,
            ))
        seen[key] = citation_id
        return citation_id

    finding_refs: dict[str, list[str]] = {}
    finding_basis: dict[str, list[FindingBasis]] = {}
    for issue in review.issues:
        refs: list[str] = []
        basis: list[FindingBasis] = []
        for idx, sc in enumerate(issue.structured_citations):
            citation_id = _resolve(sc)
            if citation_id not in refs:
                refs.append(citation_id)
            basis.append(FindingBasis(
                citation_ref=citation_id,
                label=_citation_label(sc),
                rationale=_basis_rationale(issue, sc),
                is_primary=(idx == 0),
            ))
        finding_refs[issue.issue_id] = refs
        finding_basis[issue.issue_id] = basis

    for rec in new_records:
        reporting_registry.register(rec)
    return finding_refs, finding_basis


def _finding_record(
    issue: ReviewIssue,
    citation_refs: list[str],
    basis_entries: list[FindingBasis],
) -> FindingRecord:
    """Losslessly map one ``ReviewIssue`` to a ``FindingRecord`` (T01 table)."""
    statement = _plain(issue.risk_analysis, issue.title or issue.issue_id)
    return FindingRecord(
        finding_id=issue.issue_id,
        requirement_id=_plain(issue.clause_id, issue.issue_id),
        title=issue.title,
        risk_level=issue.severity.value,
        risk_score=issue.risk_score,
        statement=statement,
        legal_basis=list(issue.citation_sources),
        recommendation=issue.recommendation,
        suggested_revision=_flatten_suggested_revision(issue),
        facts_uncertain=issue.facts_uncertain,
        review_confidence=issue.review_confidence,
        citation_refs=citation_refs,
        status=_finding_status(issue.severity.value),
        basis_entries=basis_entries,
        original_excerpt=issue.original_excerpt or None,
        clause_type=issue.clause_type.value,
        problem_type=issue.problem_type,
        clause_id=issue.clause_id,
        file_id=issue.file_id,
        source_position=(issue.position.model_dump() if issue.position else None),
        secondary_clause_types=[t.value for t in issue.secondary_clause_types],
        uncertainty_rationale=issue.uncertainty_rationale,
        review_method=issue.review_method.value,
        review_depth=issue.review_depth.value,
    )


def _missing_items_blocks(review: AggregatedReview) -> list:
    if not review.missing_items:
        return [ParagraphBlock(block_id="review.s5.empty", text="未发现全局缺失项，文档条款覆盖较完整。")]
    items = [
        ListItem(text=f"[{m.severity.value}] {m.title}：{m.description}")
        for m in review.missing_items
    ]
    return [ListBlock(block_id="review.s5.missing", ordered=False, items=items)]


def build_document_review_ir(
    *,
    task_id: str,
    document_title: str,
    review: AggregatedReview,
    sections: list[tuple[str, list[str]]] | None = None,  # deprecated shim — ignored
    citation_registry: LegacyCitationRegistry,
    model: str,
    generated_at: datetime | None = None,
) -> tuple[DocumentIR, CitationRegistry]:
    """Build v4 DocumentIR from structured ``AggregatedReview`` (authoritative)."""
    del sections  # retained for backward-compatible signature only
    reporting_registry = legacy_registry_to_reporting(citation_registry)
    timestamp = generated_at or datetime.now(timezone.utc)

    finding_refs, finding_basis = _resolve_structured_citations(review, reporting_registry)
    finding_records = [
        _finding_record(issue, finding_refs.get(issue.issue_id, []), finding_basis.get(issue.issue_id, []))
        for issue in review.issues
    ]

    # ── s6: finding summary (references only, no duplicated body) ──
    summary_blocks: list = []
    if finding_records:
        summary_blocks.append(FindingSummaryBlock(
            block_id="review.s6.summary",
            finding_refs=[f.finding_id for f in finding_records],
        ))
    else:
        summary_blocks.append(ParagraphBlock(block_id="review.s6.empty", text="未发现明显的合规问题。"))

    # ── s7: one primary display per finding ──
    detail_blocks = [
        FindingDetailBlock(block_id=f"review.s7.detail.{f.finding_id}", finding_ref=f.finding_id)
        for f in finding_records
    ] or [ParagraphBlock(block_id="review.s7.empty", text="（无逐条问题明细）")]

    # ── s8: priority actions (free-form remediation roadmap) ──
    if review.priority_actions:
        action_blocks: list = [ListBlock(
            block_id="review.s8.actions",
            ordered=True,
            items=[ListItem(text=_plain(item, "未命名行动")) for item in review.priority_actions],
        )]
    else:
        action_blocks = [ParagraphBlock(block_id="review.s8.empty", text="无优先整改行动。")]

    # ── s9: citation appendix pointers (stable IDs, not label walls) ──
    all_refs: list[str] = []
    for f in finding_records:
        for cid in f.citation_refs:
            if cid not in all_refs:
                all_refs.append(cid)
    citation_blocks: list = []
    if all_refs:
        citation_blocks.append(CitationNoteBlock(block_id="review.s9.citations", citation_refs=all_refs))
    else:
        citation_blocks.append(ParagraphBlock(block_id="review.s9.empty", text="未检索到法规依据。"))

    # ── s2: review method + document meta ──
    meta = review.review_metadata or {}
    doc_profile = review.document_profile or {}
    overview_items = [
        _kv("审查模式", str(meta.get("review_mode", "未知"))),
        _kv("文档类型", str(doc_profile.get("document_type", "未识别"))),
        _kv("文档名称", str(doc_profile.get("document_title", document_title))),
        _kv("审查条款数", str(doc_profile.get("total_clauses", "0"))),
        _kv("发现问题总数", str(doc_profile.get("total_issues_found", len(review.issues)))),
        _kv("全局缺失项数", str(doc_profile.get("total_missing_items", len(review.missing_items)))),
    ]

    # ── s3: document profile + clause distribution ──
    profile_blocks: list = [KeyValueBlock(
        block_id="review.s3.profile",
        items=[_kv(k, str(v)) for k, v in doc_profile.items()] or [_kv("文档类型", "未识别")],
    )]
    if review.clauses_summary:
        profile_blocks.append(TableBlock(
            block_id="review.s3.clauses",
            headers=["条款类型", "数量"],
            rows=[[str(k), str(v)] for k, v in review.clauses_summary.items()],
        ))

    # ── s4: risk assessment ──
    risk_items = [
        _kv("总体风险等级", review.overall_rating),
        _kv("风险评分", f"{review.overall_risk_score}/100"),
        _kv("高风险问题", str(review.issue_counts.get("HIGH", 0))),
        _kv("中风险问题", str(review.issue_counts.get("MEDIUM", 0))),
        _kv("低风险问题", str(review.issue_counts.get("LOW", 0))),
        _kv("全局缺失项", str(len(review.missing_items))),
    ]
    risk_blocks: list = [KeyValueBlock(block_id="review.s4.risk", items=risk_items)]
    for warning in review.consistency_warnings:
        risk_blocks.append(WarningBlock(
            block_id=f"review.s4.warning.{len(risk_blocks)}",
            text=_plain(warning, "跨文档一致性警告"),
            severity="warning",
        ))

    # ── s10: boundary ──
    boundary_blocks = [
        ParagraphBlock(
            block_id="review.s10.boundary",
            text="本报告由自动化审查系统生成，仅供参考，不构成正式法律意见。审查范围限于已上传文档的文本内容，无法核查事实真伪或未提供的信息。",
        ),
    ]
    if meta.get("review_mode") == "rule_only":
        boundary_blocks.append(WarningBlock(
            block_id="review.s10.ruleonly",
            text="当前审查模式为规则兜底，所有发现均基于规则匹配，建议启用LLM深度审查并人工复核。",
            severity="warning",
        ))

    sections_ir = [
        SectionIR(
            section_id="review.s1",
            title="执行摘要",
            level=1,
            ordinal="1",
            blocks=[
                ParagraphBlock(block_id="review.s1.summary", text=_plain(review.summary, "（无摘要）")),
                KeyValueBlock(block_id="review.s1.rating", items=[
                    _kv("总体合规评级", review.overall_rating),
                    _kv("风险评分", f"{review.overall_risk_score}/100"),
                ]),
            ],
        ),
        SectionIR(section_id="review.s2", title="审查概况与方法", level=1, ordinal="2",
                  blocks=[KeyValueBlock(block_id="review.s2.overview", items=overview_items)]),
        SectionIR(section_id="review.s3", title="文档画像", level=1, ordinal="3", blocks=profile_blocks),
        SectionIR(section_id="review.s4", title="整体风险评估", level=1, ordinal="4", blocks=risk_blocks),
        SectionIR(section_id="review.s5", title="完整性检查", level=1, ordinal="5",
                  blocks=_missing_items_blocks(review)),
        SectionIR(section_id="review.s6", title="问题摘要", level=1, ordinal="6", blocks=summary_blocks),
        SectionIR(section_id="review.s7", title="逐条问题", level=1, ordinal="7", blocks=detail_blocks),
        SectionIR(section_id="review.s8", title="优先整改路线图", level=1, ordinal="8", blocks=action_blocks),
        SectionIR(section_id="review.s9", title="法规依据汇总", level=1, ordinal="9", blocks=citation_blocks),
        SectionIR(section_id="review.s10", title="审查边界与置信度", level=1, ordinal="10", blocks=boundary_blocks),
    ]

    document = DocumentIR(
        document_id=f"review:{task_id}",
        report_type="review",
        identity=Identity(document_id=f"review:{task_id}", report_id=task_id, module_key="review"),
        lifecycle=Lifecycle(created_at=timestamp, state="DRAFT", report_status="DRAFT"),
        findings=finding_records,
        actions=[],
        citations=list(reporting_registry.records().values()),
        metadata=ReportMetadata(
            title=f"{document_title} — 智能审查报告",
            company_name=document_title,
            jurisdiction="CN",
            report_date=timestamp.date().isoformat(),
            report_id=task_id,
        ),
        sections=sections_ir,
        provenance=Provenance(generated_at=timestamp),
        compiler_version="0.1.0",
        prompt_version="review-structured-v4",
        template_version="review-v0",
        model=model,
    )
    return document, reporting_registry
