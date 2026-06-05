"""CPRAService — structured compliance diagnosis with rule engine + attachment extractor."""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path

from backend.common.citation.id_generator import generate_citation_id
from backend.common.citation.models import CitationItem
from backend.common.citation.output import build_knowledge_url, write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.llm.client import LLMClient
from backend.common.llm.postprocess import convert_citation_markers
from backend.common.llm.module_generator import generate_chapter
from backend.common.render.artifacts import bundle_files, render_pdf_report, render_simple_xlsx
from backend.common.render.report import (
    format_date_stamp, render_docx_template, render_markdown_template, safe_filename,
)
from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.thoughts import summarize_agent_output
from backend.common.trace.recorder import TraceRecorder
from backend.modules.cpra.attachment_extractor import CPRAAttachmentExtractor
from backend.modules.cpra.agents import create_cpra_agents
from backend.modules.cpra.fact_merger import CPRAFactMerger
from backend.modules.cpra.gap_merger import CPRAGapMerger
from backend.modules.cpra.gap_rules import run_all_rules
from backend.modules.cpra.legal_retriever import CPRALegalRetriever
from backend.modules.cpra.schema import (
    CPRAAsyncAccepted,
    CPRAAsyncStatus,
    CPRAChapter,
    CPRACitationRef,
    CPRAGapItem,
    CPRARequest,
    CPRAResult,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/4.2_cpra_panorama_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/4.2_cpra_panorama_template_v0.md")

CPRA_CHAPTERS = [
    "执行摘要",
    "企业适用性与范围",
    "数据处理活动合规分析",
    "消费者权利保障评估",
    "敏感信息与第三方管理",
    "行动清单与优先级",
]

logger = logging.getLogger(__name__)


class CPRAService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="cpra")
        self.extractor = CPRAAttachmentExtractor(parser=self.parser)
        self.legal_retriever = CPRALegalRetriever()
        self.fact_merger = CPRAFactMerger()
        self.gap_merger = CPRAGapMerger()
        self.agents = create_cpra_agents(llm_client)
        self._citation_seq_by_key: dict[tuple[str, str, str], int] = {}

    def generate_report(
        self,
        payload: CPRARequest,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> CPRAResult:
        timings: list[tuple[str, float]] = []
        t0 = time.perf_counter()
        run_task_id = task_id or uuid.uuid4().hex

        def mark(stage: str) -> None:
            nonlocal t0
            now = time.perf_counter()
            timings.append((stage, now - t0))
            t0 = now

        trace, token = prepare_run(module="cpra", task_id=run_task_id, trace=trace)
        try:
            self._citation_seq_by_key = {}
            citation_registry = CitationRegistry()

            # ── 开始事件 ──
            if trace:
                trace.record("status", {"summary": "开始 CPRA 合规诊断", "detail": {"module": "cpra", "company": payload.company_name}})
                trace.record("thought", {"summary": "路径判断：基于企业规模和数据处理范围确定 CPRA 适用条款范围"})

            # ── Attachment extraction ──
            if trace:
                trace.record("tool_start", {"summary": "附件事实提取器", "detail": {"tool": "CPRAAttachmentExtractor"}})
            attachment_facts: list[dict] = []
            fact_packs = []
            for att in payload.attachments:
                raw_facts = self.extractor.extract(att)
                attachment_facts.append(raw_facts)
                fact_packs.append(
                    self.agents["fact_extraction"].run(
                        attachment=att,
                        raw_facts=raw_facts,
                        business_model=payload.business_model,
                        data_lifecycle=payload.data_lifecycle,
                    )
                )
            mark("attachment_extraction_and_fact_agents")
            if trace:
                trace.record("tool_result", {
                    "summary": f"附件提取完成：{len(attachment_facts)} 个附件，{len(fact_packs)} 个事实包",
                    "detail": {"attachment_count": len(attachment_facts), "fact_pack_count": len(fact_packs)},
                })
                for fp in fact_packs:
                    thought = summarize_agent_output("CPRA 事实提取", fp, input_hint="附件事实抽取")
                    trace.record("thought", {"summary": thought})

            # ── 事实合并前 ──
            if trace:
                trace.record("tool_start", {"summary": "事实合并器", "detail": {"tool": "CPRAFactMerger"}})
            enhanced_payload = self.fact_merger.merge(payload, fact_packs)
            mark("fact_merge")
            if trace:
                trace.record("intermediate", {
                    "summary": "事实合并完成",
                    "detail": {
                        "category": "facts",
                        "data_item_count": len(enhanced_payload.data_items),
                        "vendor_count": len(enhanced_payload.vendors),
                    },
                })

            # ── Rule engine ──
            if trace:
                trace.record("tool_start", {"summary": "差距分析规则引擎", "detail": {"tool": "CPRA Gap Rules"}})
            gap_items = run_all_rules(
                applicability=enhanced_payload.applicability,
                business_text=enhanced_payload.business_model,
                notice_text=enhanced_payload.notice_and_consent,
                dsr=enhanced_payload.dsr_mechanism,
                dsr_text=enhanced_payload.consumer_rights_process,
                opt_out_text=enhanced_payload.opt_out_and_sale_sharing,
                data_items=enhanced_payload.data_items,
                vendors=enhanced_payload.vendors,
                consent_ui=enhanced_payload.consent_ui,
            )
            mark("rule_engine")
            if trace:
                trace.record("intermediate", {
                    "summary": f"差距分析完成：{len(gap_items)} 项差距",
                    "detail": {
                        "category": "gap_items",
                        "data": [{"domain": g.domain, "risk_level": g.risk_level, "gap": g.gap} for g in gap_items],
                    },
                })

            # ── Fallback: old rules if no structured input ──
            if not gap_items and enhanced_payload.applicability is None and not enhanced_payload.data_items:
                if trace:
                    trace.record("warning", {"summary": "结构化输入缺失，启用回退规则"})
                gap_items = self._build_legacy_gap_items(enhanced_payload)
            mark("legacy_fallback")

            # ── SPI review ──
            if trace:
                trace.record("tool_start", {"summary": "敏感信息共享风险评估", "detail": {"agent": "spi_sharing_risk"}})
            spi_review = self.agents["spi_sharing_risk"].run(
                data_items=enhanced_payload.data_items,
                vendors=enhanced_payload.vendors,
                dsr_mechanism=enhanced_payload.dsr_mechanism,
                consent_ui=enhanced_payload.consent_ui,
                notice_facts=next((fact for fact in attachment_facts if fact.get("role") == "privacy_policy"), {}),
                data_map_facts=next((fact for fact in attachment_facts if fact.get("role") == "data_map"), {}),
                vendor_facts=next((fact for fact in attachment_facts if fact.get("role") == "vendor_list"), {}),
            )
            gap_items = self.gap_merger.merge(gap_items, spi_review.gap_candidates)
            mark("spi_review")
            if trace:
                thought = summarize_agent_output("敏感信息共享风险评估", spi_review)
                trace.record("thought", {"summary": thought})
                trace.record("tool_result", {
                    "summary": f"SPI 风险评估完成：{len(spi_review.gap_candidates)} 个候选差距",
                    "detail": {"spi_gap_count": len(spi_review.gap_candidates)},
                })

            # ── Vendor review ──
            if trace:
                trace.record("tool_start", {"summary": "供应商合同合规审查", "detail": {"agent": "vendor_contract"}})
            vendor_review = self.agents["vendor_contract"].run(
                vendor_list_facts=next((fact for fact in attachment_facts if fact.get("role") == "vendor_list"), {}),
                contract_texts=[payload.vendor_management] if payload.vendor_management else [],
                vendors=enhanced_payload.vendors,
                data_items=enhanced_payload.data_items,
                opt_out_context=enhanced_payload.opt_out_and_sale_sharing,
            )
            gap_items = self.gap_merger.merge(gap_items, vendor_review.contract_gaps)
            mark("vendor_review")
            if trace:
                thought = summarize_agent_output("供应商合同合规审查", vendor_review)
                trace.record("thought", {"summary": thought})
                trace.record("tool_result", {
                    "summary": f"供应商审查完成：{len(vendor_review.contract_gaps)} 个合同差距",
                    "detail": {"vendor_gap_count": len(vendor_review.contract_gaps)},
                })

            # ── Dynamic RAG per gap/domain ──
            if trace:
                trace.record("tool_start", {"summary": "法规检索与引用匹配", "detail": {"tool": "CPRALegalRetriever"}})
            self._attach_gap_citations(gap_items, citation_registry)
            mark("attach_gap_citations")
            if trace:
                cited = sum(1 for g in gap_items if g.citations)
                trace.record("tool_result", {"summary": f"法规引用匹配完成：{cited} 项差距有法规引用"})

            # ── Rating ──
            risk_level = self._resolve_overall_level(gap_items)
            mark("resolve_rating")
            if trace:
                trace.record("intermediate", {
                    "summary": f"综合风险评级：{risk_level}",
                    "detail": {"category": "risk_level", "value": risk_level},
                })

            # ── Attachment notes ──
            attachment_notes = self._extract_attachment_notes(enhanced_payload)
            mark("attachment_notes")

            # ── Build context block with facts ──
            context_block = self._build_enhanced_context(enhanced_payload, gap_items, risk_level)
            mark("build_context")

            # ── Chapters ──
            if trace:
                trace.record("tool_start", {"summary": "报告章节生成", "detail": {"agent": "chapter_generation"}})
            all_citations = self._collect_chapter_citation_refs(gap_items, limit=6)
            chapters = self._generate_chapters_from_context(
                context_block, risk_level, all_citations, citation_registry,
            )
            mark("generate_chapters")
            if trace:
                thought = summarize_agent_output("CPRA 章节生成", chapters)
                trace.record("thought", {"summary": thought})

            # ── Consistency ──
            if trace:
                trace.record("tool_start", {"summary": "一致性审查", "detail": {"agent": "consistency_review"}})
            issues = self._check_consistency(enhanced_payload, gap_items, attachment_facts)
            consistency_review = self.agents["consistency_review"].run(
                payload_summary={
                    "company_name": enhanced_payload.company_name,
                    "has_spi": any(item.is_sensitive for item in enhanced_payload.data_items),
                    "vendor_count": len(enhanced_payload.vendors),
                },
                gap_items=gap_items,
                chapters=chapters,
            )
            issues.extend(issue.issue for issue in consistency_review.issues)
            mark("consistency_review")
            if trace:
                thought = summarize_agent_output("CPRA 一致性审查", consistency_review)
                trace.record("thought", {"summary": thought})
                trace.record("tool_result", {
                    "summary": f"一致性审查完成：{len(consistency_review.issues)} 个问题",
                    "detail": {"issues": [i.issue for i in consistency_review.issues]} if consistency_review.issues else {},
                })

            # ── Render ──
            if trace:
                trace.record("tool_start", {"summary": "报告渲染输出"})
            outputs = self._render(
                run_task_id,
                enhanced_payload,
                chapters,
                gap_items,
                attachment_notes,
                citation_registry,
            )
            mark("render")

            # ── Final events ──
            if trace:
                high_count = sum(1 for g in gap_items if g.risk_level == "HIGH")
                medium_count = sum(1 for g in gap_items if g.risk_level == "MEDIUM")
                low_count = sum(1 for g in gap_items if g.risk_level == "LOW")

                trace.record("final", {
                    "summary": f"CPRA 合规诊断完成：{high_count} 项高风险，{medium_count} 项中风险，{low_count} 项低风险",
                    "detail": {
                        "output_files": outputs,
                        "risk_distribution": {"HIGH": high_count, "MEDIUM": medium_count, "LOW": low_count},
                        "total_duration_ms": int(sum(d for _, d in timings) * 1000),
                    },
                })

                trace.record("final_brief", {
                    "summary": "CPRA 合规诊断完成",
                    "detail": {
                        "conclusion": f"完成 CPRA 合规全景诊断，识别 {high_count} 项高风险、{medium_count} 项中风险差距",
                        "files": list(outputs.values()),
                        "risks": [
                            {"severity": "HIGH", "count": high_count},
                            {"severity": "MEDIUM", "count": medium_count},
                            {"severity": "LOW", "count": low_count},
                        ],
                        "next_steps": [
                            "优先处理所有 HIGH 风险差距项，制定短期整改计划",
                            "核查一致性审查中发现的问题",
                            "补充缺失的隐私政策附件和数据处理协议",
                            "建议每半年复审一次 CPRA 合规状态",
                        ],
                        "stats": {
                            "total_duration_seconds": round(sum(d for _, d in timings), 1),
                            "gap_count": len(gap_items),
                            "output_files_count": len(outputs),
                        },
                    },
                })

                if os.getenv("AI4LAW_CPRA_PROFILE") == "1":
                    logger.warning(
                        "CPRA generate_report timings: %s",
                        ", ".join(f"{name}={duration:.3f}s" for name, duration in timings),
                    )

                return CPRAResult(
                    report_path=outputs["docx"],
                    output_files=outputs,
                    company_name=payload.company_name,
                    risk_level=risk_level,
                    gap_items=gap_items,
                    chapters=chapters,
                    consistency_issues=issues,
                    attachment_notes=attachment_notes,
                )
        finally:
            finalize_run(token)

    def _attach_gap_citations(self, gap_items: list[CPRAGapItem], citation_registry: CitationRegistry) -> None:
        high_medium_gaps = [
            gap for gap in gap_items if gap.risk_level in ("HIGH", "MEDIUM")
        ]
        per_gap = self.legal_retriever.retrieve_for_gaps(high_medium_gaps[:8])
        domain_cache: dict[str, list[dict]] = {}
        for gap in gap_items:
            gap.citations = []
            gap.citation_refs = []

        for idx, gap in enumerate(high_medium_gaps[:8]):
            key = self.legal_retriever._gap_key(gap, idx)  # noqa: SLF001
            hits = per_gap.get(key, [])
            if hits:
                self._apply_gap_citation_hits(gap, hits[:2], citation_registry)
            else:
                if gap.domain not in domain_cache:
                    domain_cache[gap.domain] = self.legal_retriever.retrieve(gap.domain)
                self._apply_gap_citation_hits(gap, domain_cache.get(gap.domain, [])[:2], citation_registry)

        for gap in gap_items:
            if not gap.citations:
                if gap.domain not in domain_cache:
                    domain_cache[gap.domain] = self.legal_retriever.retrieve(gap.domain)
                self._apply_gap_citation_hits(gap, domain_cache.get(gap.domain, [])[:2], citation_registry)

    # ── Async ───────────────────────────────────────────────────────────

    def submit_async(self, payload: CPRARequest) -> CPRAAsyncAccepted:
        task_id = uuid.uuid4().hex
        trace_recorder = TraceRecorder(trace_dir=Path("outputs/cpra") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            runner=lambda: self.generate_report(payload, task_id=task_id, trace=trace_recorder),
            trace_recorder=trace_recorder,
        )
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> CPRAAsyncStatus:
        return self._snapshot_to_status(self.tasks.get_or_raise(task_id))

    def retry_async(self, task_id: str) -> CPRAAsyncStatus:
        return self._snapshot_to_status(self.tasks.retry(task_id))

    def cancel_async(self, task_id: str) -> CPRAAsyncStatus:
        return self._snapshot_to_status(self.tasks.cancel(task_id))

    # ── Legacy fallback ─────────────────────────────────────────────────

    def _build_legacy_gap_items(self, payload: CPRARequest) -> list[CPRAGapItem]:
        """Original 4-rule fallback for backward compat (no structured fields)."""
        items: list[CPRAGapItem] = []
        notice_text = payload.notice_and_consent.lower()
        rights_text = payload.consumer_rights_process.lower()
        sale_text = payload.opt_out_and_sale_sharing.lower()
        vendor_text = payload.vendor_management.lower()

        if any(token in notice_text for token in ("缺失", "无", "none")):
            items.append(CPRAGapItem(domain="notice_and_consent", risk_level="HIGH",
                gap="隐私告知或同意机制不完整",
                legal_basis="CPRA Notice at Collection 要求",
                recommendation="补齐分场景告知文本与同意留痕机制", phase="short_term"))
        if "45" not in rights_text and "sla" not in rights_text:
            items.append(CPRAGapItem(domain="consumer_rights_process", risk_level="MEDIUM",
                gap="消费者权利响应时限与SLA未明确",
                legal_basis="CPRA 消费者权利响应时限要求",
                recommendation="建立统一DSR流程并设置45天响应时限监控", phase="short_term"))
        if any(token in sale_text for token in ("yes", "是", "出售", "共享")) and "opt-out" not in sale_text:
            items.append(CPRAGapItem(domain="opt_out_and_sale_sharing", risk_level="HIGH",
                gap="存在出售/共享但未明确 opt-out 机制",
                legal_basis="CPRA Sale/Sharing opt-out 要求",
                recommendation="上线 Do Not Sell/Share 链接并记录执行日志", phase="short_term"))
        if payload.vendor_management and "dpa" not in vendor_text:
            items.append(CPRAGapItem(domain="vendor_management", risk_level="MEDIUM",
                gap="供应商管理未体现 DPA/服务商条款",
                legal_basis="CPRA 服务商与第三方管理要求",
                recommendation="补齐供应商分类与DPA签署台账", phase="mid_term"))
        if not items:
            items.append(CPRAGapItem(domain="overall", risk_level="LOW",
                gap="未识别明显高风险差距",
                legal_basis="输入范围内未命中高风险规则",
                recommendation="保持半年复审并更新证据材料", phase="long_term"))
        return items

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_overall_level(items: list[CPRAGapItem]) -> str:
        levels = {item.risk_level for item in items}
        if "HIGH" in levels: return "HIGH"
        if "MEDIUM" in levels: return "MEDIUM"
        return "LOW"

    def _build_enhanced_context(self, payload: CPRARequest, gaps: list[CPRAGapItem], level: str) -> str:
        gap_summary = "；".join(f"{g.domain}:{g.gap}" for g in gaps[:10])
        facts_block = ""
        if payload.applicability:
            facts_block += f"\n- 年收入: {payload.applicability.annual_revenue_usd or '未提供'}\n"
            facts_block += f"- 加州消费者数: {payload.applicability.ca_consumer_count or '未提供'}\n"
        if payload.data_items:
            facts_block += "- 数据项:\n"
            for di in payload.data_items[:8]:
                facts_block += f"  * {di.category} (SPI={di.is_sensitive}, 出售={di.sale_or_share})\n"
        if payload.dsr_mechanism:
            d = payload.dsr_mechanism
            facts_block += f"- DSR渠道: web={d.has_web_form} email={d.has_email} phone={d.has_toll_free_phone}\n"
        if payload.vendors:
            facts_block += f"- 供应商数: {len(payload.vendors)}\n"
        return (
            f"【企业信息】\n- 企业名称：{payload.company_name}\n"
            f"- 业务模型：{payload.business_model}\n"
            f"- 数据生命周期：{payload.data_lifecycle}\n"
            f"【结构化事实】{facts_block}\n"
            f"【合规差距摘要】{gap_summary}\n"
            f"【风险等级】{level}\n"
        )

    def _generate_chapters_from_context(
        self,
        context_block: str,
        level: str,
        citations: list[CPRACitationRef],
        citation_registry: CitationRegistry,
    ) -> list[CPRAChapter]:
        chapters: list[CPRAChapter] = []
        citation_ids = [item.citation_id for item in citations]
        marker_block = citation_registry.build_marker_list()
        chapter_context = context_block
        if citations:
            chapter_context = f"{context_block}\n【可引用法规依据】\n{marker_block}\n"
        for idx, title in enumerate(CPRA_CHAPTERS, start=1):
            if self.llm_client and self.llm_client.enabled:
                content = generate_chapter(
                    self.llm_client,
                    "cpra",
                    title,
                    chapter_context,
                    citations=[item.display_label for item in citations],
                    citation_marker_section=marker_block,
                    use_citation_markers=True,
                )
                content = convert_citation_markers(content, citation_registry)
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(
                CPRAChapter(
                    chapter_no=idx,
                    title=title,
                    content=content,
                    citations=list(citation_ids),
                    citation_refs=list(citations),
                    risk_level=level,
                )
            )
        return chapters

    def _extract_attachment_notes(self, payload: CPRARequest) -> list[str]:
        notes: list[str] = []
        for item in payload.attachments:
            if item.file_format == "url":
                notes.append(f"{item.file_name}: [url] {item.storage_uri}")
                continue
            try:
                text = self.parser.parse_text(item.storage_uri)
                notes.append(f"{item.file_name}: {text[:160].replace(chr(10), ' ')}")
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{item.file_name}: [parse skipped] {exc}")
        return notes

    @staticmethod
    def _check_consistency(payload: CPRARequest, gaps: list[CPRAGapItem], facts: list[dict]) -> list[str]:
        issues: list[str] = []
        has_policy = any(item.file_role == "privacy_policy" for item in payload.attachments)
        if not has_policy:
            issues.append("Missing privacy_policy attachment or URL reference.")
        if any(g.risk_level == "HIGH" for g in gaps):
            issues.append("Contains HIGH risk gaps; remediation should be scheduled in short_term phase.")
        return issues

    def _render(self, task_id: str, payload, chapters, gaps, attachment_notes, citation_registry: CitationRegistry) -> dict[str, str]:
        sections: list[tuple[str, str]] = [
            ("输入摘要", payload.model_dump_json(indent=2)),
            ("差距清单摘要", "\n".join(f"- [{g.risk_level}] {g.domain}: {g.gap}" for g in gaps)),
            ("附件解析摘要", "\n".join(f"- {item}" for item in attachment_notes) or "- 无"),
        ]
        for ch in chapters:
            sections.append((f"第{ch.chapter_no}章 {ch.title}", ch.content))

        output_dir = Path("outputs/cpra") / task_id / "outputs"
        date_stamp = format_date_stamp()
        base = safe_filename(payload.company_name)
        md_out = output_dir / f"{base}_CPRA_合规全景报告_草案_{date_stamp}.md"
        docx_out = output_dir / f"{base}_CPRA_合规全景报告_草案_{date_stamp}.docx"
        pdf_out = output_dir / f"{base}_CPRA_合规全景报告_草案_{date_stamp}.pdf"
        xlsx_out = output_dir / f"{base}_CPRA_整改路线图_草案_{date_stamp}.xlsx"
        zip_out = output_dir / f"{base}_CPRA_输出包_草案_{date_stamp}.zip"

        output_dir.mkdir(parents=True, exist_ok=True)
        mapping = _build_template_mapping(payload, chapters, gaps, date_stamp)
        render_markdown_template(md_out, TEMPLATE_MD, mapping)
        render_docx_template(docx_out, TEMPLATE_PATH, mapping)
        render_pdf_report(pdf_out, "加州CPRA合规全景报告（草案）", sections)
        headers = ["domain", "risk_level", "gap", "legal_basis", "recommendation", "phase", "evidence_source"]
        rows = [[g.domain, g.risk_level, g.gap, g.legal_basis, g.recommendation, g.phase, g.evidence_source] for g in gaps]
        render_simple_xlsx(xlsx_out, headers=headers, rows=rows)
        bundle_files(zip_out, [docx_out, md_out, pdf_out, xlsx_out])
        footnote_map = {
            str(num): item.to_dict()
            for num, item in citation_registry.get_footnote_map().items()
        }
        citation_map_json = write_citation_map_json(
            output_dir=output_dir,
            module="cpra",
            task_id=task_id,
            footnote_map=footnote_map,
            all_items=citation_registry.to_list(),
        )
        return {
            "markdown": str(md_out),
            "docx": str(docx_out),
            "pdf": str(pdf_out),
            "xlsx": str(xlsx_out),
            "zip": str(zip_out),
            "citation_map_json": citation_map_json,
        }

    def _apply_gap_citation_hits(
        self,
        gap: CPRAGapItem,
        hits: list[dict],
        citation_registry: CitationRegistry,
    ) -> None:
        refs: list[CPRACitationRef] = []
        ids: list[str] = []
        for hit in hits:
            ref = self._citation_ref_from_hit(hit, gap, citation_registry)
            if ref is None:
                continue
            refs.append(ref)
            ids.append(ref.citation_id)
        gap.citation_refs = refs
        gap.citations = ids

    def _citation_ref_from_hit(
        self,
        hit: dict,
        gap: CPRAGapItem,
        citation_registry: CitationRegistry,
    ) -> CPRACitationRef | None:
        source_id = str(hit.get("source_id", "") or "").strip()
        source_title = str(hit.get("source_title", "") or hit.get("title", "") or "").strip()
        article_no = str(hit.get("article_no", "") or "").strip()
        if not source_id or not source_title:
            return None

        seq_key = ("US", source_id, article_no or "GEN")
        seq = self._citation_seq_by_key.get(seq_key, 0) + 1
        self._citation_seq_by_key[seq_key] = seq
        abbr = self._citation_abbr(source_id, source_title)
        citation_id = generate_citation_id("US", abbr, article_no or "GEN", seq)
        display_label = str(hit.get("display_label", "") or hit.get("source", "") or source_title).strip()
        snippet = str(hit.get("snippet", "") or hit.get("content", "") or "")[:500]
        confidence_score = float(hit.get("confidence_score", hit.get("score", 0.0)) or 0.0)
        authority_level = str(hit.get("authority_level", "medium") or "medium")
        binding_force = str(hit.get("binding_force", "mandatory") or "mandatory")
        citation_type = str(hit.get("citation_type", "law_article") or "law_article")
        source_kind = str(hit.get("source_kind", "law_article") or "law_article")
        knowledge_url = build_knowledge_url(source_id=source_id, article_no=article_no) or ""

        item = CitationItem(
            citation_id=citation_id,
            source_id=source_id,
            jurisdiction="US",
            display_label=display_label,
            citation_type=citation_type,
            title=source_title,
            article_no=article_no,
            quote_text=snippet,
            related_issue_ids=[gap.domain],
            confidence_score=confidence_score,
            authority_level=authority_level,
            binding_force=binding_force,
            source_kind=source_kind,
            confidence_threshold=0.20,
            external_report_allowed=confidence_score >= 0.20,
        )
        citation_registry.register(item)
        return CPRACitationRef(
            citation_id=citation_id,
            source_id=source_id,
            source_title=source_title,
            article_no=article_no,
            display_label=display_label,
            snippet=snippet,
            confidence_score=confidence_score,
            authority_level=authority_level,
            binding_force=binding_force,
            citation_type=citation_type,
            source_kind=source_kind,
            jurisdiction="US",
            knowledge_url=knowledge_url,
        )

    @staticmethod
    def _citation_abbr(source_id: str, source_title: str) -> str:
        if source_id == "us_cpra":
            return "CPRA"
        if source_id == "us_cppa_regulations":
            return "CPPA"
        title = (source_title or "").upper()
        if "CPPA" in title:
            return "CPPA"
        if "CPRA" in title or "CCPA" in title:
            return "CPRA"
        return "USLAW"

    @staticmethod
    def _collect_chapter_citation_refs(gap_items: list[CPRAGapItem], limit: int) -> list[CPRACitationRef]:
        refs: list[CPRACitationRef] = []
        seen: set[str] = set()
        for gap in gap_items:
            for ref in gap.citation_refs:
                if ref.citation_id in seen:
                    continue
                refs.append(ref)
                seen.add(ref.citation_id)
                if len(refs) >= limit:
                    return refs
        return refs

    @staticmethod
    def _snapshot_to_accepted(s: TaskSnapshot) -> CPRAAsyncAccepted:
        return CPRAAsyncAccepted(task_id=s.task_id, module=s.module, state=s.state, attempts=s.attempts, max_attempts=s.max_attempts)

    @staticmethod
    def _snapshot_to_status(s: TaskSnapshot) -> CPRAAsyncStatus:
        result = CPRAResult.model_validate(s.result) if s.result else None
        return CPRAAsyncStatus(task_id=s.task_id, module=s.module, state=s.state, attempts=s.attempts, max_attempts=s.max_attempts, created_at=s.created_at, updated_at=s.updated_at, error=s.error, result=result)


def _build_template_mapping(payload, chapters, gaps, date_stamp):
    def pick(no):
        for c in chapters:
            if c.chapter_no == no: return c.content
        return ""
    gap_summary = "; ".join(f"[{g.risk_level}] {g.domain}: {g.gap}" for g in gaps) or "暂无"
    return {
        "current_state": pick(2) or "企业业务与数据处理现状概述。",
        "cpra_mapping": pick(3) or "依据CPRA条款进行映射分析。",
        "gaps_and_risks": gap_summary,
        "remediation_roadmap": pick(6) or "按优先级制定整改路线图。",
        "final_conclusion": f"评估日期：{date_stamp}。",
    }
