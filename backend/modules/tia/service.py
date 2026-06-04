"""TIAService — transfer impact assessment with structured fact assessment."""

from __future__ import annotations

import uuid
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import (
    format_date_stamp, render_docx_template, render_markdown_template, safe_filename,
)
from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.thoughts import summarize_agent_output
from backend.modules.tia.attachment_evidence import TIAAttachmentEvidence
from backend.modules.tia.country_risk import TIACountryRiskAssessor
from backend.modules.tia.data_sensitivity import TIADataSensitivity
from backend.modules.tia.measure_sufficiency import TIAMeasureSufficiency
from backend.modules.tia.route_decider import TIARouteDecider
from backend.modules.tia.agents import create_tia_agents
from backend.modules.tia.schema import (
    TIAAsyncAccepted, TIAAsyncStatus, TIAChapter, TIARequest, TIAResult,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/3.4_tia_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/3.4_tia_template_v0.md")

TIA_CHAPTERS = [
    "跨境传输场景与角色识别",
    "传输工具适用性判断",
    "第三国法律与实践评估",
    "补充措施可执行性评估",
    "剩余风险与合规结论",
    "持续复审与行动计划",
]


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
            if trace:
                trace.record("status", {"summary": "开始 TIA 传输影响评估", "detail": {"module": "tia"}})
                trace.record("thought", {"summary": "路径判断：基于传输工具类型和目的地法律环境确定 TIA 评估范围"})

            route = None
            country_risk_result = None
            measure_assessments = []
            measure_overall = "unknown"
            effective_risk = "MEDIUM"
            data_sens = {}

            if payload.structured_input:
                route = self.route_decider.decide(payload.transfer_tool, payload.structured_input)
                country_risk_result = self.country_risk.assess(payload.structured_input)
                data_sens = self.data_sensitivity.assess(payload.structured_input)
                risk_level_str = country_risk_result.risk_level
                if risk_level_str == "VERY_HIGH" or data_sens.get("sensitivity") == "very_high":
                    effective_risk = "VERY_HIGH"
                elif risk_level_str == "HIGH" or data_sens.get("risk_factor", 1.0) >= 1.5:
                    effective_risk = "HIGH"
                else:
                    effective_risk = risk_level_str
                measure_assessments, measure_overall = self.measure_sufficiency.assess(
                    payload.structured_input, effective_risk,
                )
                if effective_risk == "VERY_HIGH" or measure_overall == "insufficient":
                    level = "HIGH"
                elif effective_risk == "HIGH" or measure_overall == "conditional":
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
                    hits = retrieve_regulations(q["query"], top_k=3, jurisdiction="eu", path="all")
                    all_regs.extend(hits)
                except Exception:
                    pass
            if not all_regs:
                all_regs = retrieve_regulations(
                    f"TIA EDPB transfer tool {payload.transfer_tool} {dest} third country law assessment",
                    top_k=5, jurisdiction="eu", path="all",
                )
            seen_ids = set()
            regs = []
            for r in all_regs:
                rid = getattr(r, "id", str(r))
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    regs.append(r)
            regs = regs[:8]
            citations = [f"{item.title}{item.article}" for item in regs]
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
                    attachment_evidences.append(self.attachment_evidence.extract(att))
                except (FileNotFoundError, ValueError) as exc:
                    attachment_notes.append(f"{att.file_name}: [parse skipped] {exc}")
                    attachment_evidences.append({"parse_error": True})

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

            context_block = self._build_context(payload, level, route, country_risk_result,
                                                 data_sens, measure_assessments, reg_snippet)

            chapters: list[TIAChapter] = []
            for idx, title in enumerate(TIA_CHAPTERS, start=1):
                if self.llm_client and self.llm_client.enabled:
                    content = generate_chapter(self.llm_client, "tia", title, context_block, citations=citations)
                else:
                    content = f"（{title}：LLM未配置，此处为占位内容）"
                chapters.append(TIAChapter(chapter_no=idx, title=title, content=content, citations=citations, risk_level=level))

            dpo_review = self.agents["dpo_review"].run(
                route=route.route if route else "unknown",
                country_risk_level=country_risk_result.risk_level if country_risk_result else "MEDIUM",
                sensitivity=data_sens.get("sensitivity", "unknown"),
                measure_overall=measure_overall if (payload.structured_input and measure_overall) else "unknown",
                effective_risk=effective_risk if payload.structured_input else level,
                issues=[],
                chapter_summaries=[{
                    "no": ch.chapter_no, "title": ch.title, "content": ch.content[:300],
                } for ch in chapters],
            )
            if trace:
                thought = summarize_agent_output("TIA DPO审查", dpo_review)
                trace.record("thought", {"summary": thought})

            if dpo_review.get("non_reliance_warning_needed"):
                chapters[0].content = (
                    "⚠️ 重要警告：不应仅依赖本TIA草案启动传输。"
                    "建议在实施前寻求主管监管机构指导或批准。\n\n" + chapters[0].content
                )
            if dpo_review.get("dpo_position"):
                chapters[0].content += f"\n\n**DPO意见**: {dpo_review['dpo_position']}"
            if dpo_review.get("mandatory_conditions"):
                chapters[5].content += (
                    "\n\n**强制前置条件**:\n" +
                    "\n".join(f"- {c}" for c in dpo_review["mandatory_conditions"])
                )

            issues = self._check_consistency(payload, level, route, country_risk_result,
                                              data_sens, measure_assessments, attachment_evidences)

            outputs = self._render(run_task_id, payload, chapters, attachment_notes)

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
                        "risks": [],
                        "next_steps": ["复核 TIA 评估结论", "确认补充措施的充分性"],
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
            )
        finally:
            finalize_run(token)

    # ── Context builder ──

    def _build_context(self, payload, level, route, country_risk_result,
                       data_sens, measure_assessments, reg_snippet):
        lines = [
            f"【传输信息】",
            f"- 传输工具：{payload.transfer_tool}",
            f"- 数据出口方：{payload.data_exporter_profile}",
            f"- 数据进口方：{payload.data_importer_profile}",
            f"- 第三国法律评估：{payload.third_country_assessment}",
            f"- 补充措施：{payload.supplementary_measures}",
            f"- 最终结论：{payload.final_conclusion}",
            f"- 风险等级：{level}",
        ]
        if route:
            lines.append(f"\n【路径判断】")
            lines.append(f"- 评估路径：{route.route}")
            lines.append(f"- 需要完整TIA：{'是' if route.need_full_tia else '否'}")
            lines.append(f"- 理由：{route.reason}")
            if route.adequacy_decision_exists:
                lines.append(f"- 充分性决定国家：{route.adequacy_country}")
        if country_risk_result:
            lines.append(f"\n【国家风险评估】")
            lines.append(f"- 国家：{country_risk_result.country}")
            lines.append(f"- 风险等级：{country_risk_result.risk_level}")
            lines.append(f"- 风险来源：{'; '.join(country_risk_result.risk_sources)}")
            lines.append(f"- 政府访问风险：{'是' if country_risk_result.gov_access_risk else '否'}")
            lines.append(f"- 补充说明：{country_risk_result.notes}")
        if data_sens:
            lines.append(f"\n【数据敏感性】")
            lines.append(f"- 敏感等级：{data_sens.get('sensitivity', 'unknown')}")
            lines.append(f"- 风险系数：{data_sens.get('risk_factor', 1.0)}")
            if data_sens.get("special_categories"):
                lines.append(f"- 特殊类别数据：{', '.join(data_sens['special_categories'])}")
        if measure_assessments:
            lines.append(f"\n【补充措施评估】")
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
        )
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> TIAAsyncStatus:
        return self._snapshot_to_status(self.tasks.get_or_raise(task_id))

    def retry_async(self, task_id: str) -> TIAAsyncStatus:
        return self._snapshot_to_status(self.tasks.retry(task_id))

    def cancel_async(self, task_id: str) -> TIAAsyncStatus:
        return self._snapshot_to_status(self.tasks.cancel(task_id))

    # ── Render ──

    def _render(self, task_id: str, payload: TIARequest, chapters: list[TIAChapter], attachment_notes: list[str]) -> dict[str, str]:
        output_dir = Path("outputs/tia") / task_id / "outputs"
        date_stamp = format_date_stamp()
        base_name = safe_filename(f"{payload.data_exporter_profile}_{payload.transfer_tool}_TIA")
        md_output = output_dir / f"{base_name}_报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{base_name}_报告_草案_{date_stamp}.docx"
        zip_output = output_dir / f"{base_name}_输出包_草案_{date_stamp}.zip"
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping = _build_template_mapping(payload, chapters)
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}

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


def _build_template_mapping(payload: TIARequest, chapters: list[TIAChapter]) -> dict[str, str]:
    def pick(no: int) -> str:
        for ch in chapters:
            if ch.chapter_no == no: return ch.content
        return ""
    return {
        "transfer_context": pick(1) or f"{payload.data_exporter_profile} -> {payload.data_importer_profile}",
        "transfer_tool": pick(2) or payload.transfer_tool,
        "third_country_analysis": pick(3) or payload.third_country_assessment,
        "supplementary_measures": pick(4) or payload.supplementary_measures,
        "final_assessment": "\n".join(filter(None, [pick(5), pick(6), payload.final_conclusion])),
    }
