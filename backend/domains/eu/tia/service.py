"""TIAService — transfer impact assessment with structured fact assessment."""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

from backend.common.citation.module_grounding import (
    CitationBundle,
    ModuleIssue,
    build_module_citation_bundle,
)
from backend.common.citation.locators import normalize_article_no
from backend.common.citation.output import build_knowledge_url
from backend.common.citation.registry import CitationRegistry
from backend.common.llm.client import LLMClient
from backend.common.llm.postprocess import apply_citation_pipeline
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.service import retrieve_legal_documents
from backend.common.knowledge.paths import regulation_articles_jsonl_path
from backend.common.rag.ingest import load_regulation_rows
from backend.common.rag.retriever import RegulationDoc
from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.thoughts import summarize_agent_output
from backend.domains.eu.tia.agents import create_tia_agents
from backend.domains.eu.tia.attachment_evidence import TIAAttachmentEvidence
from backend.domains.eu.tia.country_risk import TIACountryRiskAssessor
from backend.domains.eu.tia.data_sensitivity import TIADataSensitivity
from backend.domains.eu.tia.decision_policy import (
    build_decision_chapter_text,
    evaluate_tia_decision,
)
from backend.domains.eu.tia.deterministic_chapters import build_deterministic_tia_chapters
from backend.domains.eu.tia.measure_sufficiency import TIAMeasureSufficiency
from backend.domains.eu.tia.report_renderer import TIAReportRenderer
from backend.domains.eu.tia.route_decider import TIARouteDecider
from backend.domains.eu.tia.schema import (
    TIAAsyncAccepted, TIAAsyncStatus, TIAChapter, TIARequest, TIAResult,
)
from backend.domains.us.cpra.schema import CPRACitationRef

TIA_CHAPTERS = [
    "跨境传输场景与角色识别",
    "传输工具适用性判断",
    "第三国法律与实践评估",
    "补充措施可执行性评估",
    "剩余风险与合规结论",
    "持续复审与行动计划",
]

MANDATORY_TIA_LOCATORS = (
    ("EU-LAW-001", "44"),
    ("EU-LAW-001", "46"),
    ("EU-GUIDE-002", "Step 3"),
)


@lru_cache(maxsize=1)
def _mandatory_tia_regulations() -> tuple[RegulationDoc, ...]:
    """Resolve decision-bearing authorities by canonical source and locator."""
    required = {
        (source_id, normalize_article_no(article_no))
        for source_id, article_no in MANDATORY_TIA_LOCATORS
    }
    documents: list[RegulationDoc] = []
    for row in load_regulation_rows(regulation_articles_jsonl_path()):
        key = (
            str(row.get("source_id", "")),
            normalize_article_no(str(row.get("article_ref", ""))),
        )
        if key not in required:
            continue
        documents.append(RegulationDoc(
            id=key[0],
            title=str(row.get("law_name", "")),
            article=str(row.get("article_ref", "")),
            content=str(row.get("content", "")),
            jurisdiction=str(row.get("jurisdiction", "")),
            path=str(row.get("path", "")),
            doc_type=str(row.get("doc_type", "")),
            source_url=str(row.get("source_url", "")),
            snapshot_path=str(row.get("snapshot_path", "")),
            keywords=tuple(str(item) for item in row.get("keywords", [])),
        ))
    return tuple(documents)


def _dedupe_regulations(regulations: list) -> list:
    deduped: list = []
    seen: set[tuple[str, str]] = set()
    for regulation in regulations:
        identity = (
            str(getattr(regulation, "id", regulation)),
            str(getattr(regulation, "article", "")),
        )
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(regulation)
    return deduped


class TIAService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="tia")
        # NEW components
        self.route_decider = TIARouteDecider()
        self.country_risk = TIACountryRiskAssessor()
        self.data_sensitivity = TIADataSensitivity()
        self.measure_sufficiency = TIAMeasureSufficiency()
        self.attachment_evidence = TIAAttachmentEvidence(parser=self.parser)
        self.agents = create_tia_agents(llm_client)
        from backend.core.settings import get_settings as _gs
        _settings = _gs()
        self.renderer = TIAReportRenderer(
            schema_first_enabled=_settings.schema_first_tia_enabled,
            model_name=_settings.resolved_llm_model,
        )

    def generate_report(
        self,
        payload: TIARequest,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> TIAResult:
        run_task_id = task_id or uuid.uuid4().hex
        _, token = prepare_run(module="tia", task_id=run_task_id, trace=trace)
        # ── Structured assessment (NEW) ──
        try:
            citation_registry = CitationRegistry()
            if trace:
                trace.record("status", {"summary": "开始 TIA 传输影响评估", "detail": {"module": "tia"}})
                trace.record("thought", {"summary": "路径判断：基于传输工具类型和目的地法律环境确定 TIA 评估范围"})

            route = None
            country_risk_result = None
            measure_assessments = []
            measure_overall = "unknown"
            inherent_risk = "MEDIUM"
            data_sens = {}

            if payload.structured_input:
                route = self.route_decider.decide(payload.transfer_tool, payload.structured_input)
                country_risk_result = self.country_risk.assess(payload.structured_input)
                data_sens = self.data_sensitivity.assess(payload.structured_input)
                risk_level_str = country_risk_result.risk_level
                if risk_level_str == "VERY_HIGH" or data_sens.get("sensitivity") == "very_high":
                    inherent_risk = "VERY_HIGH"
                elif risk_level_str == "HIGH" or data_sens.get("risk_factor", 1.0) >= 1.5:
                    inherent_risk = "HIGH"
                else:
                    inherent_risk = risk_level_str
                measure_assessments, measure_overall = self.measure_sufficiency.assess(
                    payload.structured_input, inherent_risk,
                )
                if inherent_risk == "VERY_HIGH" or measure_overall == "insufficient":
                    level = "HIGH"
                elif inherent_risk == "HIGH" or measure_overall == "conditional":
                    level = "MEDIUM"
                else:
                    level = "LOW"
            else:
                level = self._resolve_risk_level(payload.third_country_assessment, payload.final_conclusion)

            # ── Agent 1: RAG Planning — multi-query targeted retrieval ──
            dest = ""
            if payload.structured_input:
                dest = payload.structured_input.destination_country or payload.structured_input.importer_country
            agent_rag = self.agents["rag_planning"].run(
                transfer_tool=payload.transfer_tool, dest_country=dest,
                data_categories=list(payload.structured_input.data_categories) if payload.structured_input else [],
                sensitivity=data_sens.get("sensitivity", "unknown"),
                country_risk_level=country_risk_result.risk_level if country_risk_result else "MEDIUM",
                has_spi=payload.structured_input.has_special_category_data if payload.structured_input else False,
                gov_access_risk=country_risk_result.gov_access_risk if country_risk_result else False,
                route=route.route if route else "unknown",
            )
            if trace:
                thought = summarize_agent_output("TIA RAG检索规划", agent_rag)
                trace.record("thought", {"summary": thought})

            all_regs: list = []
            reg_queries = agent_rag.get("queries", [])
            for q in reg_queries[:4]:
                try:
                    hits = retrieve_legal_documents(
                        q["query"],
                        module="eu_tia",
                        top_k=3,
                        jurisdiction="eu",
                        path="all",
                    ).documents
                    all_regs.extend(hits)
                except Exception:
                    pass
            if not all_regs:
                all_regs = retrieve_legal_documents(
                    f"TIA EDPB transfer tool {payload.transfer_tool} {dest} third country law assessment",
                    module="eu_tia",
                    top_k=5,
                    jurisdiction="eu",
                    path="all",
                ).documents
            regs = _dedupe_regulations([
                *_mandatory_tia_regulations(),
                *all_regs,
            ])[:12]
            reg_snippet = "\n".join(
                f"- {item.title}{item.article}：{(item.content or '')[:120]}"
                for item in regs
            ) or "（暂无检索到相关法条）"

            attachment_notes: list[str] = []
            attachment_evidences: list[dict] = []
            for att in payload.attachments:
                try:
                    text = self.parser.parse_text(att.storage_uri)
                    attachment_notes.append(f"{att.file_name}: {text[:160].replace(chr(10), ' ')}")
                    attachment_evidences.append(
                        self.attachment_evidence.extract(att, text=text)
                    )
                except (FileNotFoundError, ValueError) as exc:
                    attachment_notes.append(f"{att.file_name}: [parse skipped] {exc}")
                    attachment_evidences.append({"role": att.file_role, "parse_error": True})

            ta_ev = next((e for e in attachment_evidences if e.get("role") == "transfer_agreement"), None)
            cl_ev = next((e for e in attachment_evidences if e.get("role") == "country_law_analysis"), None)
            tc_ev = next((e for e in attachment_evidences if e.get("role") == "technical_control_doc"), None)
            si_summary = {}
            if payload.structured_input:
                si_summary = {
                    "encryption_before_transfer": payload.structured_input.encryption_before_transfer,
                    "key_managed_in_eu": payload.structured_input.key_managed_in_eu,
                    "has_secure_enclave": payload.structured_input.has_secure_enclave,
                    "has_key_separation": payload.structured_input.has_key_separation,
                }
            agent_att = self.agents["attachment_review"].run(
                transfer_agreement_evidence=ta_ev,
                country_law_evidence=cl_ev,
                technical_control_evidence=tc_ev,
                structured_input_summary=si_summary,
            )
            if trace:
                thought = summarize_agent_output("TIA 附件审查", agent_att)
                trace.record("thought", {"summary": thought})

            # Inject evidence review findings into attachment_notes for report display
            for conflict in agent_att.get("conflicts", []):
                attachment_notes.append(f"[证据冲突] {conflict}")
            for missing in agent_att.get("missing_evidence", []):
                attachment_notes.append(f"[缺失证据] {missing}")

            issues = self._check_consistency(
                payload,
                level,
                route,
                country_risk_result,
                data_sens,
                measure_assessments,
                attachment_evidences,
            )
            decision = evaluate_tia_decision(
                transfer_tool=payload.transfer_tool,
                structured_input=payload.structured_input,
                inherent_risk=inherent_risk if payload.structured_input else level,
                residual_risk=level,
                measure_sufficiency=(
                    measure_overall if payload.structured_input else "unknown"
                ),
                attachment_evidences=attachment_evidences,
                consistency_issues=issues,
            )
            if decision.transfer_status == "suspend":
                system_issue = "[系统决策] 关键证据或风险门槛未满足，必须暂停传输。"
                if system_issue not in issues:
                    issues.append(system_issue)

            context_block = self._build_context(payload, level, route, country_risk_result,
                                                 data_sens, measure_assessments, reg_snippet,
                                                 decision=decision)

            citation_bundle = self._build_tia_citation_bundle(
                payload=payload,
                regs=regs,
                level=level,
                route=route,
                country_risk_result=country_risk_result,
                measure_overall=measure_overall,
            )
            citation_registry._items = dict(citation_bundle.registry._items)  # noqa: SLF001
            citation_refs = self._bundle_to_refs(citation_bundle)
            marker_by_article = {
                str(item.article_no).lower(): f"{{{{{item.citation_id}}}}}"
                for item in citation_bundle.items
            }
            fallback_chapters = build_deterministic_tia_chapters(
                payload=payload,
                route=route,
                country_risk=country_risk_result,
                data_sensitivity=data_sens,
                measures=measure_assessments,
                decision=decision,
                citation_markers=marker_by_article,
            )

            chapters: list[TIAChapter] = []
            for idx, title in enumerate(TIA_CHAPTERS, start=1):
                if self.llm_client and self.llm_client.enabled:
                    content = generate_chapter(
                        self.llm_client,
                        "tia",
                        title,
                        f"{context_block}\n【可引用法规依据】\n{citation_bundle.prompt_block}\n",
                        citations=[ref.display_label for ref in citation_refs],
                        citation_marker_section=citation_bundle.prompt_block,
                        use_citation_markers=True,
                        citation_registry=citation_registry,
                    )
                    content = apply_citation_pipeline(
                        content,
                        registry=citation_registry,
                        allowed_citations=[ref.display_label for ref in citation_refs],
                    ).text
                else:
                    content = fallback_chapters.get(idx, "")
                    content = apply_citation_pipeline(
                        content,
                        registry=citation_registry,
                        allowed_citations=[ref.display_label for ref in citation_refs],
                    ).text
                chapters.append(
                    TIAChapter(
                        chapter_no=idx,
                        title=title,
                        content=content,
                        citations=[ref.citation_id for ref in citation_refs],
                        citation_refs=citation_refs,
                        risk_level=level,
                    )
                )

            decision_markers = [
                marker_by_article[key]
                for key in ("46", "step 3")
                if key in marker_by_article
            ]
            decision_text, action_text = build_decision_chapter_text(
                decision,
                proposed_conclusion=payload.final_conclusion,
                citation_markers=decision_markers,
            )
            for chapter, deterministic_text in zip(
                chapters[4:6],
                (decision_text, action_text),
                strict=True,
            ):
                chapter.content = apply_citation_pipeline(
                    deterministic_text,
                    registry=citation_registry,
                    allowed_citations=[ref.display_label for ref in citation_refs],
                ).text

            dpo_review = self.agents["dpo_review"].run(
                route=route.route if route else "unknown",
                country_risk_level=country_risk_result.risk_level if country_risk_result else "MEDIUM",
                sensitivity=data_sens.get("sensitivity", "unknown"),
                measure_overall=measure_overall if (payload.structured_input and measure_overall) else "unknown",
                residual_risk=decision.residual_risk,
                issues=issues,
                chapter_summaries=[{
                    "no": ch.chapter_no, "title": ch.title, "content": ch.content[:300],
                } for ch in chapters],
            )
            if trace:
                thought = summarize_agent_output("TIA DPO审查", dpo_review)
                trace.record("thought", {"summary": thought})

            if decision.transfer_status == "suspend" or dpo_review.get("non_reliance_warning_needed"):
                chapters[0].content = (
                    "⚠️ 重要警告：不应仅依赖本TIA草案启动传输。"
                    "系统规则要求在问题修复并完成正式复核前暂停传输。\n\n" + chapters[0].content
                )
            review_position = str(dpo_review.get("dpo_position", "")).strip()
            if decision.transfer_status == "suspend":
                review_position = (
                    "规则结论要求暂停传输；补齐证据并完成正式 DPO 复核前不得启动或继续。"
                )
            if review_position:
                chapters[0].content += (
                    "\n\n**AI辅助复核意见（不构成DPO正式签署）**: " + review_position
                )
            if (
                decision.transfer_status != "suspend"
                and dpo_review.get("mandatory_conditions")
            ):
                chapters[5].content += (
                    "\n\n**AI辅助补充建议（不构成正式批准条件）**:\n" +
                    "\n".join(f"- {c}" for c in dpo_review["mandatory_conditions"])
                )

            for critical_issue in dpo_review.get("critical_issues", []):
                if isinstance(critical_issue, str) and critical_issue.strip():
                    if critical_issue.strip() in issues:
                        continue
                    dpo_issue = f"[DPO复核] {critical_issue.strip()}"
                    if dpo_issue not in issues:
                        issues.append(dpo_issue)

            outputs = self._render(run_task_id, payload, chapters, attachment_notes, citation_registry)

            if trace:
                trace.record("final", {
                    "summary": "TIA 传输影响评估完成",
                    "detail": {"output_files": outputs if isinstance(outputs, dict) else {}},
                })
                trace.record("final_brief", {
                    "summary": "TIA 传输影响评估完成",
                    "detail": {
                        "conclusion": "TIA 传输影响评估已完成",
                        "files": list(outputs.values()) if isinstance(outputs, dict) else [],
                        "risks": issues,
                        "next_steps": (
                            decision.mandatory_conditions
                            if decision.transfer_status == "suspend"
                            else (["修复 DPO 复核问题", "重新审阅 TIA 结论"]
                                  if dpo_review.get("review_result") in ("needs_revision", "rejected")
                                  else ["复核 TIA 评估结论", "确认补充措施的充分性"])
                        ),
                    },
                })

            return TIAResult(
                report_path=outputs["docx"],
                output_files=outputs,
                transfer_tool=payload.transfer_tool,
                risk_level=level,
                chapters=chapters,
                consistency_issues=issues,
                attachment_notes=attachment_notes,
                route_decision=route,
                country_risk=country_risk_result,
                measure_assessments=measure_assessments,
                decision=decision,
            )
        finally:
            finalize_run(token)

    # ── Context builder ──

    def _build_context(self, payload, level, route, country_risk_result,
                       data_sens, measure_assessments, reg_snippet, decision=None):
        lines = [
            "【传输信息】",
            f"- 传输工具：{payload.transfer_tool}",
            f"- 数据出口方：{payload.data_exporter_profile}",
            f"- 数据进口方：{payload.data_importer_profile}",
            f"- 第三国法律评估：{payload.third_country_assessment}",
            f"- 补充措施：{payload.supplementary_measures}",
            f"- 最终结论：{payload.final_conclusion}",
            f"- 风险等级：{level}",
        ]
        if decision:
            lines.extend([
                f"- 系统传输决定：{decision.transfer_status}",
                f"- 固有风险：{decision.inherent_risk}",
                f"- 剩余风险：{decision.residual_risk}",
                f"- 证据状态：{decision.evidence_status}",
                "- 约束：模型不得覆盖系统传输决定",
            ])
        if payload.structured_input:
            lines.append(f"- 数据出口方 GDPR 角色：{payload.structured_input.exporter_role}")
            lines.append(f"- 数据进口方 GDPR 角色：{payload.structured_input.importer_role}")
        if route:
            lines.append("\n【路径判断】")
            lines.append(f"- 评估路径：{route.route}")
            lines.append(f"- 需要完整TIA：{'是' if route.need_full_tia else '否'}")
            lines.append(f"- 理由：{route.reason}")
            if route.adequacy_decision_exists:
                lines.append(f"- 充分性决定国家：{route.adequacy_country}")
        if country_risk_result:
            lines.append("\n【国家风险评估】")
            lines.append(f"- 国家：{country_risk_result.country}")
            lines.append(f"- 风险等级：{country_risk_result.risk_level}")
            lines.append(f"- 风险来源：{'; '.join(country_risk_result.risk_sources)}")
            lines.append(f"- 政府访问风险：{'是' if country_risk_result.gov_access_risk else '否'}")
            lines.append(f"- 补充说明：{country_risk_result.notes}")
        if data_sens:
            lines.append("\n【数据敏感性】")
            lines.append(f"- 敏感等级：{data_sens.get('sensitivity', 'unknown')}")
            lines.append(f"- 风险系数：{data_sens.get('risk_factor', 1.0)}")
            if data_sens.get("special_categories"):
                lines.append(f"- 特殊类别数据：{', '.join(data_sens['special_categories'])}")
        if measure_assessments:
            lines.append("\n【补充措施评估】")
            for m in measure_assessments:
                suf = "充足" if m.sufficient_for_risk else "不足"
                lines.append(f"- [{suf}] {m.measure_name}: {m.assessment}")
        lines.append(f"\n【法规参考】\n{reg_snippet}")
        return "\n".join(lines)

    # ── Risk resolution ──

    @staticmethod
    def _resolve_risk_level(third_country_assessment: str, final_conclusion: str) -> str:
        text = f"{third_country_assessment} {final_conclusion}".lower()
        if any(token in text for token in ("高", "high", "不可", "cannot", "not effective")):
            return "HIGH"
        if any(token in text for token in ("中", "medium", "条件", "conditional")):
            return "MEDIUM"
        return "LOW"

    # ── Consistency ──

    def _check_consistency(self, payload, level, route, country_risk, data_sens, measures, evidences):
        issues: list[str] = []
        # Original checks
        has_law = any(att.file_role == "country_law_analysis" for att in payload.attachments)
        if not has_law:
            issues.append("No country_law_analysis attachment provided.")
        if payload.transfer_tool == "scc" and "scc" not in payload.final_conclusion.lower():
            issues.append("Transfer tool is SCC but conclusion doesn't evaluate SCC effectiveness.")
        if level == "HIGH" and "暂停" not in payload.final_conclusion and "suspend" not in payload.final_conclusion.lower():
            issues.append("Risk is HIGH; consider adding transfer suspension decision.")

        # NEW checks
        if payload.structured_input:
            if payload.structured_input.exporter_role == "unknown":
                issues.append("Data exporter GDPR role is not confirmed.")
            if payload.structured_input.importer_role == "unknown":
                issues.append("Data importer GDPR role is not confirmed.")

        # Route consistency
        if route and route.adequacy_decision_exists and payload.transfer_tool != "derogation":
            issues.append(f"Adequacy decision exists for {route.adequacy_country}; "
                          f"full TIA via {payload.transfer_tool} may be unnecessary.")

        # Country risk + measure gap
        if country_risk and country_risk.risk_level in ("HIGH", "VERY_HIGH"):
            if not payload.structured_input or not payload.structured_input.encryption_before_transfer:
                issues.append(f"Destination {country_risk.country} is {country_risk.risk_level} risk "
                              f"but no encryption-before-transfer confirmed.")
            if country_risk.gov_access_risk and not any(m.measure_type in ("technical_strong", "technical_extreme") for m in measures):
                issues.append(f"Government access risk in {country_risk.country} requires "
                              f"strong technical measures (encryption + EU key management).")

        # Data sensitivity + country risk escalation
        if data_sens.get("risk_factor", 1.0) >= 2.0 and country_risk and country_risk.risk_level in ("HIGH", "VERY_HIGH"):
            issues.append(f"VERY_HIGH risk combination: sensitive/special category data "
                          f"({', '.join(data_sens.get('special_categories', []))}) "
                          f"+ {country_risk.risk_level} risk destination ({country_risk.country}). "
                          f"Regulatory consultation strongly advised.")

        # SCC + no encryption for HIGH risk
        if payload.transfer_tool == "scc" and level == "HIGH":
            if payload.structured_input and not payload.structured_input.encryption_before_transfer:
                issues.append("SCC transfer to HIGH-risk country without encryption: SCC alone may be ineffective.")

        # Article 49 abuse warning
        if payload.transfer_tool == "derogation":
            issues.append("Article 49 derogation should be strictly necessary, occasional, and with explicit consent. Not suitable for systematic transfers.")

        # Evidence gaps
        scc_agreement_ev = [e for e in evidences if e.get("role") == "transfer_agreement"]
        if scc_agreement_ev and not any(e.get("has_scc_mention") for e in scc_agreement_ev):
            issues.append("Transfer agreement does not explicitly mention SCC clauses.")

        tech_ev = [e for e in evidences if e.get("role") == "technical_control_doc"]
        if tech_ev:
            for e in tech_ev:
                if e.get("has_encryption_at_rest") and not e.get("key_location_eu"):
                    issues.append("Encryption at rest detected but key location not confirmed as EU-based.")

        return issues

    # ── Async ──

    def submit_async(self, payload: TIARequest) -> TIAAsyncAccepted:
        task_id = uuid.uuid4().hex
        trace = TraceRecorder(Path("outputs/tia") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            lambda: self.generate_report(payload, task_id=task_id, trace=trace),
            trace_recorder=trace,
            llm_client=self.llm_client,
            input_snapshot=payload.model_dump(mode="json"),
        )
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> TIAAsyncStatus:
        return self._snapshot_to_status(self.tasks.get_or_raise(task_id))

    def retry_async(self, task_id: str) -> TIAAsyncStatus:
        return self._snapshot_to_status(self.tasks.retry(task_id))

    def cancel_async(self, task_id: str) -> TIAAsyncStatus:
        return self._snapshot_to_status(self.tasks.cancel(task_id))

    # ── Render ──

    def _render(
        self,
        task_id: str,
        payload: TIARequest,
        chapters: list[TIAChapter],
        attachment_notes: list[str],
        citation_registry: CitationRegistry,
    ) -> dict[str, str]:
        """Delegate to TIAReportRenderer.

        The method signature is preserved so that existing tests that monkeypatch
        or call ``service._render`` directly continue to work unchanged.
        """
        return self.renderer.render(
            task_id=task_id,
            payload=payload,
            chapters=chapters,
            attachment_notes=attachment_notes,
            citation_registry=citation_registry,
        )

    def _build_tia_citation_bundle(
        self,
        *,
        payload: TIARequest,
        regs: list,
        level: str,
        route,
        country_risk_result,
        measure_overall: str,
    ) -> CitationBundle:
        issues = _tia_module_issues(payload, level, route, country_risk_result, measure_overall)
        return build_module_citation_bundle(
            module="tia",
            jurisdiction="EU",
            issues=issues,
            regulations_by_issue=_tia_regulations_by_issue(issues, regs),
        )

    @staticmethod
    def _bundle_to_refs(bundle: CitationBundle) -> list[CPRACitationRef]:
        return [_tia_ref_from_item(item) for item in bundle.items]

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> TIAAsyncAccepted:
        return TIAAsyncAccepted(task_id=snapshot.task_id, module=snapshot.module, state=snapshot.state,
                                 attempts=snapshot.attempts, max_attempts=snapshot.max_attempts)

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> TIAAsyncStatus:
        result = TIAResult.model_validate(snapshot.result) if snapshot.result else None
        return TIAAsyncStatus(task_id=snapshot.task_id, module=snapshot.module, state=snapshot.state,
                               attempts=snapshot.attempts, max_attempts=snapshot.max_attempts,
                               created_at=snapshot.created_at, updated_at=snapshot.updated_at,
                               error=snapshot.error, result=result)


def _reg_to_dict(reg) -> dict:
    source_id = str(getattr(reg, "source_id", "") or getattr(reg, "id", "") or "")
    title = str(getattr(reg, "title", "") or "")
    article = str(getattr(reg, "article", "") or "")
    content = str(getattr(reg, "content", "") or "")
    if not source_id:
        if "GDPR" in title.upper():
            source_id = "eu_gdpr"
        elif "EDPB" in title.upper():
            source_id = "eu_edpb_recommendations"
        else:
            source_id = title.lower().replace(" ", "_")
    return {
        "source_id": source_id,
        "source_title": title,
        "title": title,
        "article": article,
        "snippet": content[:500],
        "content": content,
        "source_kind": "official_guide" if "EDPB" in title.upper() else "law_article",
        "authority_level": "medium" if "EDPB" in title.upper() else "high",
        "binding_force": "recommended" if "EDPB" in title.upper() else "mandatory",
    }


def _tia_module_issues(
    payload: TIARequest,
    level: str,
    route,
    country_risk_result,
    measure_overall: str,
) -> list[ModuleIssue]:
    issues = [
        ModuleIssue(
            issue_id="TIA-001-transfer-tool",
            category="transfer_tool",
            title=f"传输工具适用性判断：{payload.transfer_tool}",
            description=f"{payload.final_conclusion} {payload.third_country_assessment}",
            severity=level,
            legal_basis="GDPR Article 46 / Article 44",
            recommendation="确认使用的传输工具具备 Article 46 合法基础。",
        ),
        ModuleIssue(
            issue_id="TIA-002-country-risk",
            category="country_risk",
            title="第三国法律与实践评估",
            description=payload.third_country_assessment,
            severity=level,
            legal_basis="GDPR Article 44",
            recommendation="补充第三国执法访问与救济机制分析。",
        ),
        ModuleIssue(
            issue_id="TIA-003-supplementary-measures",
            category="supplementary_measures",
            title="补充措施可执行性评估",
            description=payload.supplementary_measures,
            severity=level,
            legal_basis="EDPB Recommendations 01/2020",
            recommendation="确认技术/组织/合同补充措施是否足以覆盖风险。",
        ),
    ]
    if measure_overall:
        issues.append(
            ModuleIssue(
                issue_id="TIA-004-residual-risk",
                category="residual_risk",
                title="剩余风险与合规结论",
                description=f"{payload.final_conclusion} measures={measure_overall}",
                severity=level,
                legal_basis="GDPR Article 46",
                recommendation="对剩余风险形成可审计结论。",
            )
        )
    return issues


def _tia_regulations_by_issue(issues: list[ModuleIssue], regs: list) -> dict[str, list[dict]]:
    reg_dicts = [_reg_to_dict(reg) for reg in regs]
    return {issue.issue_id: reg_dicts for issue in issues}


def _tia_ref_from_item(item) -> CPRACitationRef:
    return CPRACitationRef(
        citation_id=item.citation_id,
        source_id=item.source_id,
        source_title=item.title,
        article_no=item.article_no,
        display_label=item.display_label,
        snippet=item.quote_text,
        confidence_score=item.confidence_score,
        authority_level=item.authority_level,
        binding_force=item.binding_force,
        citation_type=item.citation_type,
        source_kind=item.source_kind,
        jurisdiction=item.jurisdiction or "EU",
        knowledge_url=build_knowledge_url(
            source_id=item.source_id, article_no=item.article_no
        ) or "",
    )
