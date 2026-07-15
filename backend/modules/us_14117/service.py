"""US 14117 service — WorkflowPipeline orchestration for EO 14117 compliance assessment."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.service import retrieve_legal_documents
from backend.common.render.artifacts import bundle_files, render_pdf_report, render_simple_xlsx
from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.common.render.summary import attach_citations, summarize_for_slot
from backend.common.storage.file_parser import FileParser
from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.thoughts import summarize_agent_output
from backend.common.workflow import GenerationContextPack, WorkflowPipeline
from backend.modules.us_14117.evidence_builder import build_us_14117_evidence
from backend.modules.us_14117.fact_builder import build_us_14117_facts
from backend.modules.us_14117.issue_builder import US_14117_CHAPTER_KEYS, build_us_14117_issues
from backend.modules.us_14117.rule_engine import run_rule_engine
from backend.modules.us_14117.agents import create_us14117_agents
from backend.modules.us_14117.schema import (
    US14117AsyncAccepted,
    US14117AsyncStatus,
    US14117Chapter,
    US14117Request,
    US14117Result,
    US14117RuleEngineResult,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/4.2_us_14117_compliance_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/4.2_us_14117_compliance_template_v0.md")

US_14117_CHAPTERS = [
    "总体结论与传输可行性",
    "风险详情与分析",
    "合规措施建议与行动清单",
    "附件与持续监控",
]


class US14117Service:
    """EO 14117 compliance assessment service with deterministic rule engine."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="us_14117")
        self.agents = create_us14117_agents(llm_client)

    def generate_report(
        self,
        payload: US14117Request,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> US14117Result:
        run_task_id = task_id or str(uuid.uuid4())
        trace, token = prepare_run(module="us_14117", task_id=run_task_id, trace=trace)

        if trace:
            trace.record("status", {"state": "started"})
            trace.record("thought", {"summary": "路径判断：输入解析与规则引擎触发，评估是否有必要启动 US 14117 流程"})

        # Run rule engine BEFORE pipeline
        rule_result = run_rule_engine(payload)
        trace.record("rule_engine_result", rule_result.model_dump())

        # ── Agent 1: Rule Boundary — review uncertain classifications ──
        uncertain_entities = [
            ea for ea in rule_result.entity_assessments
            if ea.get("confidence", 1.0) < 0.85 and ea.get("is_covered_person")
        ]
        boundary_items = [
            dc for dc in rule_result.data_classifications
            if dc.get("threshold_hit") and 0.9 <= dc.get("us_person_count", 0) / max(dc.get("bulk_threshold", 1), 1) <= 1.1
        ]
        if uncertain_entities or boundary_items:
            agent_rb = self.agents["rule_boundary"].run(
                uncertain_entities=uncertain_entities,
                boundary_items=boundary_items,
                ambiguous_tx=rule_result.transaction_classification.get("transaction_type") == "other",
                tx_description=payload.transaction_description,
            )
            for override in agent_rb.get("overrides", []):
                for ea in rule_result.entity_assessments:
                    if ea.get("entity_name") == override.get("entity_name"):
                        if override.get("recommended_status") == "needs_review":
                            ea["flag_for_dpo"] = True
            trace.record("agent_rule_boundary", agent_rb)
            if trace:
                thought = summarize_agent_output("US 14117 规则边界", agent_rb)
                trace.record("thought", {"summary": thought})

        self._trace = trace
        try:
            run_result = self._build_pipeline(rule_result).run(
                payload=payload, task_id=run_task_id, trace=trace
            )
        finally:
            self._trace = None
            finalize_run(token)

        if trace:
            trace.record("status", {"state": "completed"})
            trace.record("thought", {"summary": "最终输出：组装 US 14117 评估报告并返回结果"})

        return US14117Result(
            report_path=run_result.outputs.get("markdown", ""),
            output_files=run_result.outputs,
            company_name=payload.company_name,
            overall_traffic_light=rule_result.traffic_light.overall_light,
            traffic_light_result=rule_result.traffic_light,
            risk_matrix=rule_result.risk_matrix,
            rule_hits=rule_result.all_rule_hits,
            chapters=run_result.chapters,
            consistency_issues=run_result.consistency_issues,
            attachment_notes=[
                f"{item.get('source_ref', '')}: {item.get('summary', '')}"
                for item in run_result.context_pack.attachment_notes
            ],
        )

    def _build_pipeline(self, rule_result: US14117RuleEngineResult) -> WorkflowPipeline:
        return WorkflowPipeline(
            extract_profile=lambda payload: payload,
            evaluate_diagnosis=lambda payload: rule_result,
            validate_path=lambda payload, path, rationale: None,
            build_facts=self._build_facts(rule_result),
            retrieve_regulations=self._retrieve_regulations,
            build_attachment_notes=self._extract_attachment_notes,
            build_issues=self._build_issues(rule_result),
            build_evidence=self._build_evidence,
            build_context_pack=self._build_context_pack(rule_result),
            generate_chapters=self._generate_chapters_from_pack(rule_result),
            check_consistency=self._check_consistency_with_context,
            check_alignment=lambda content, profile: [],
            render_artifacts=self._render_outputs(rule_result),
            request_event_name="us_14117_request",
            consistency_check_labels=["us_14117_rules", "context_pack_references"],
        )

    def _build_facts(self, rule_result: US14117RuleEngineResult):
        def _inner(payload: US14117Request, profile: US14117Request, diagnosis: US14117RuleEngineResult):
            return build_us_14117_facts(payload, rule_result)
        return _inner

    def _retrieve_regulations(self, _: US14117Request) -> list[dict]:
        # ── Agent 3: RAG Reformulation — generate targeted query ──
        query = "EO 14117 restricted transaction covered person security measures"
        agent_rag = self.agents["rag_reformulation"].run(
            rule_hit_summary=[], data_categories=[], transaction_type="vendor_agreement", covered_person_count=0,
        )
        _t = getattr(self, "_trace", None)
        if _t:
            _t.record("agent_rag_reformulation", agent_rag)
            thought = summarize_agent_output("US 14117 RAG检索重构", agent_rag)
            _t.record("thought", {"summary": thought})
        if agent_rag.get("primary_query"):
            query = agent_rag["primary_query"]
        docs = retrieve_legal_documents(
            query,
            module="us_eo14117",
            top_k=6,
            jurisdiction="us",
            path="eo14117",
        ).documents
        return [
            {
                "source_id": item.id,
                "title": item.title,
                "article": item.article,
                "snippet": item.content,
            }
            for item in docs
        ]

    def _extract_attachment_notes(self, payload: US14117Request) -> list[dict[str, str]]:
        notes: list[dict[str, str]] = []
        for file_path in payload.attachments:
            try:
                text = self.parser.parse_text(file_path)
                notes.append({
                    "source_ref": file_path,
                    "summary": text[:160].replace("\n", " "),
                })
            except (FileNotFoundError, ValueError) as exc:
                notes.append({
                    "source_ref": file_path,
                    "summary": f"[parse skipped] {exc}",
                })
        return notes

    def _build_issues(self, rule_result: US14117RuleEngineResult):
        def _inner(facts, diagnosis: US14117RuleEngineResult, regulations: list[dict], attachment_notes: list[dict[str, str]]):
            return build_us_14117_issues(facts, rule_result, regulations)
        return _inner

    @staticmethod
    def _build_evidence(facts, issues, regulations, diagnosis: US14117RuleEngineResult):
        updated_issues, evidence_chain = build_us_14117_evidence(facts, issues, regulations)
        return updated_issues, evidence_chain

    def _build_context_pack(self, rule_result: US14117RuleEngineResult):
        def _inner(
            *,
            task_id: str,
            diagnosis: US14117RuleEngineResult,
            facts,
            regulations,
            issues,
            evidence_chain,
            path_warning: str | None,
            attachment_notes: list[dict[str, str]],
            **kwargs,
        ) -> GenerationContextPack:
            # ── Agent 2: Evidence Priority ──
            ev_priority_result = self.agents["evidence_priority"].run(
                risk_matrix_rows=[r.model_dump() for r in rule_result.risk_matrix],
                traffic_light=rule_result.traffic_light.overall_light,
                prohibition_reasons=rule_result.traffic_light.prohibition_reasons,
                restriction_reasons=rule_result.traffic_light.restriction_reasons,
            )
            _t = getattr(self, "_trace", None)
            if _t:
                _t.record("agent_evidence_priority", ev_priority_result)
                thought = summarize_agent_output("US 14117 证据优先级", ev_priority_result)
                _t.record("thought", {"summary": thought})

            # ── Agent 5: Repair Check ──
            repair_result = self.agents["repair_check"].run(
                issue_summaries=[{
                    "issue_id": i.issue_id, "severity": i.severity,
                    "title": i.title, "fact_refs": i.fact_refs, "rule_refs": i.rule_refs,
                } for i in issues],
                evidence_count=len(evidence_chain),
                has_attachments=bool(attachment_notes),
                traffic_light=rule_result.traffic_light.overall_light,
                missing_measures=rule_result.traffic_light.missing_security_measures,
            )
            if _t:
                _t.record("agent_repair_check", repair_result)
                thought = summarize_agent_output("US 14117 修复检查", repair_result)
                _t.record("thought", {"summary": thought})

            return GenerationContextPack(
                module_key="us_14117",
                request_id=task_id,
                facts=facts,
                diagnosis_result=diagnosis.model_dump(),
                regulations=regulations,
                issues=issues,
                evidence_chain=evidence_chain,
                path_warning=path_warning,
                risk_summary={
                    "traffic_light": rule_result.traffic_light.overall_light,
                    "is_prohibited": rule_result.traffic_light.is_prohibited,
                    "is_restricted": rule_result.traffic_light.is_restricted,
                    "agent_evidence_priority": ev_priority_result,
                    "agent_repair_check": repair_result,
                },
                attachment_notes=attachment_notes,
                output_requirements={"chapter_keys": list(US_14117_CHAPTER_KEYS.values())},
            )
        return _inner

    def _generate_chapters_from_pack(self, rule_result: US14117RuleEngineResult):
        def _inner(
            payload: US14117Request,
            regulations: list[dict],
            context_pack: GenerationContextPack,
        ) -> list[US14117Chapter]:
            citations = [
                f"{item.get('title', '')}{item.get('article', '')}"
                for item in regulations
            ]
            chapters: list[US14117Chapter] = []
            for idx, title in enumerate(US_14117_CHAPTERS, start=1):
                chapter_id = US_14117_CHAPTER_KEYS[title]
                context_block = _build_context_block(payload, context_pack, rule_result, chapter_id)
                if self.llm_client and self.llm_client.enabled:
                    content = generate_chapter(
                        self.llm_client, "us_14117", title, context_block, citations=citations
                    )
                else:
                    content = _render_placeholder_chapter(title, chapter_id, rule_result)
                chapters.append(
                    US14117Chapter(
                        chapter_no=idx,
                        title=title,
                        content=content,
                        citations=citations,
                        risk_level=rule_result.traffic_light.overall_light,
                    )
                )
            # ── Agent 4: Chapter Consistency — verify generated chapters ──
            agent_chk = self.agents["chapter_consistency"].run(
                chapter_summaries=[{
                    "no": ch.chapter_no, "title": ch.title, "content": ch.content[:400],
                } for ch in chapters],
                traffic_light=rule_result.traffic_light.overall_light,
                issue_count=len(context_pack.issues),
                missing_measures=rule_result.traffic_light.missing_security_measures,
            )
            _t = getattr(self, "_trace", None)
            if _t:
                _t.record("agent_chapter_consistency", agent_chk)
                thought = summarize_agent_output("US 14117 章节一致性", agent_chk)
                _t.record("thought", {"summary": thought})
            if not agent_chk.get("consistent", True):
                for fix in agent_chk.get("recommended_fixes", []):
                    chapters[-1].content += f"\n\n[一致性检查建议] {fix}"
            return chapters
        return _inner

    @staticmethod
    def _check_consistency_with_context(
        payload: US14117Request,
        chapters: list[US14117Chapter],
        context_pack: GenerationContextPack,
    ) -> list[str]:
        issues_list: list[str] = []
        if not payload.data_items:
            issues_list.append("Missing required data items for EO 14117 assessment.")
        if not payload.recipient_entities:
            issues_list.append("Missing recipient entities for covered person screening.")
        if any(
            item.severity in {"HIGH", "BLOCKER"}
            for item in context_pack.issues
        ):
            issues_list.append(
                "Contains HIGH/BLOCKER risk items; recommend legal escalation before proceeding."
            )
        if any(not chapter.citations for chapter in chapters):
            issues_list.append("Some chapters have no citations.")
        return issues_list

    def _render_outputs(self, rule_result: US14117RuleEngineResult):
        def _inner(
            *,
            task_id: str,
            payload: US14117Request,
            profile: US14117Request,
            regulations: list[dict],
            chapters: list[US14117Chapter],
            path_warning: str | None,
            alignment_warning: str | None,
            issues,
            evidence_chain,
            attachment_notes: list[dict[str, str]],
            trace_manifest_path: str,
            facts,
            diagnosis: US14117RuleEngineResult,
            **kwargs,
        ) -> dict[str, str]:
            sections: list[tuple[str, str]] = [
                ("输入摘要", payload.model_dump_json(indent=2)),
                (
                    "风险评估结论",
                    f"总体红黄绿: {rule_result.traffic_light.overall_light}\n"
                    f"是否禁止交易: {'是' if rule_result.traffic_light.is_prohibited else '否'}\n"
                    f"是否限制交易: {'是' if rule_result.traffic_light.is_restricted else '否'}\n"
                    f"摘要: {rule_result.traffic_light.summary}",
                ),
                (
                    "附件解析摘要",
                    "\n".join(
                        f"- {item.get('source_ref', '')}: {item.get('summary', '')}"
                        for item in attachment_notes
                    ) or "- 无",
                ),
            ]
            for chapter in chapters:
                sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

            output_dir = Path("outputs/us_14117") / task_id / "outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            date_stamp = format_date_stamp()
            base = safe_filename(payload.company_name)
            md_output = output_dir / f"{base}_14117_风险评估结论报告_草案_{date_stamp}.md"
            docx_output = output_dir / f"{base}_14117_风险评估结论报告_草案_{date_stamp}.docx"
            pdf_output = output_dir / f"{base}_14117_风险评估结论报告_草案_{date_stamp}.pdf"
            xlsx_output = output_dir / f"{base}_14117_风险矩阵_草案_{date_stamp}.xlsx"
            zip_output = output_dir / f"{base}_14117_输出包_草案_{date_stamp}.zip"

            # Markdown template rendering
            mapping = _build_template_mapping(payload, chapters, rule_result)
            if TEMPLATE_MD.exists():
                render_markdown_template(md_output, TEMPLATE_MD, mapping)
            else:
                _render_markdown_fallback(md_output, payload, chapters, rule_result, date_stamp)
            if TEMPLATE_PATH.exists():
                render_docx_template(docx_output, TEMPLATE_PATH, mapping)
            else:
                docx_output.touch()

            render_pdf_report(pdf_output, "EO 14117 风险评估结论报告（草案）", sections)

            # XLSX risk matrix
            matrix_headers = [
                "entity_name", "covered_person_status", "data_item_name",
                "data_category", "us_person_count", "threshold", "threshold_hit",
                "transaction_type", "traffic_light", "reason",
            ]
            matrix_rows = [
                [
                    row.entity_name, row.covered_person_status, row.data_item_name,
                    row.data_category, row.us_person_count, row.threshold,
                    row.threshold_hit, row.transaction_type, row.traffic_light, row.reason,
                ]
                for row in rule_result.risk_matrix
            ]
            render_simple_xlsx(xlsx_output, headers=matrix_headers, rows=matrix_rows)

            # JSON artifacts
            issue_json = output_dir / "issue_list.json"
            issue_json.write_text(
                json.dumps([item.model_dump() for item in issues], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            evidence_json = output_dir / "evidence_chain.json"
            evidence_json.write_text(
                json.dumps([item.model_dump() for item in evidence_chain], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            facts_json = output_dir / "facts.json"
            facts_json.write_text(
                json.dumps([item.model_dump() for item in facts], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            rule_engine_json = output_dir / "rule_engine_result.json"
            rule_engine_json.write_text(
                rule_result.model_dump_json(indent=2), encoding="utf-8",
            )

            trace_dest = output_dir / "trace_manifest.json"
            trace_dest.write_text(
                Path(trace_manifest_path).read_text(encoding="utf-8"), encoding="utf-8",
            )

            bundle_files(
                zip_output,
                [
                    md_output, pdf_output, xlsx_output,
                    issue_json, evidence_json, facts_json, rule_engine_json, trace_dest,
                ],
            )
            if docx_output.exists():
                bundle_files(zip_output, [docx_output])

            return {
                "markdown": str(md_output),
                "docx": str(docx_output),
                "pdf": str(pdf_output),
                "xlsx": str(xlsx_output),
                "zip": str(zip_output),
                "issue_list_json": str(issue_json),
                "evidence_chain_json": str(evidence_json),
                "facts_json": str(facts_json),
                "rule_engine_result_json": str(rule_engine_json),
                "trace_manifest": str(trace_dest),
            }
        return _inner

    # ── Async API ──

    def submit_async(self, payload: US14117Request) -> US14117AsyncAccepted:
        task_id = str(uuid.uuid4())
        trace = TraceRecorder(Path("outputs/us_14117") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            lambda: self.generate_report(payload, task_id=task_id, trace=trace),
            trace_recorder=trace,
        )
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> US14117AsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> US14117AsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> US14117AsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> US14117AsyncAccepted:
        return US14117AsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> US14117AsyncStatus:
        result = None
        if snapshot.result is not None:
            result = US14117Result.model_validate(snapshot.result)
        return US14117AsyncStatus(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            error=snapshot.error,
            result=result,
        )


# ═══════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════

def _build_context_block(
    payload: US14117Request,
    context_pack: GenerationContextPack,
    rule_result: US14117RuleEngineResult,
    chapter_id: str,
) -> str:
    """Build a rich context block for a single report chapter."""
    matched_issues = [
        item for item in context_pack.issues
        if chapter_id in item.affects_outputs
    ]
    if not matched_issues:
        matched_issues = [
            item for item in context_pack.issues
            if item.severity in {"HIGH", "BLOCKER"}
        ]

    issue_block = "\n".join(
        f"- {item.issue_id} | {item.severity} | {item.title} | {item.recommended_action}"
        for item in matched_issues
    ) or "- 无"

    reg_block = "\n".join(
        f"- {item.get('source_id', 'unknown')} | {item.get('title', '')}{item.get('article', '')}: "
        f"{str(item.get('snippet', ''))[:120]}"
        for item in context_pack.regulations[:6]
    ) or "- 无"

    evidence_block = "\n".join(
        f"- {item.evidence_id} | {item.claim} -> {item.conclusion}"
        for item in context_pack.evidence_chain
    ) or "- 无"

    # Traffic light context
    tl = rule_result.traffic_light
    tl_block = (
        f"总体红黄绿: {tl.overall_light}\n"
        f"是否禁止: {'是' if tl.is_prohibited else '否'}\n"
        f"是否限制: {'是' if tl.is_restricted else '否'}\n"
        f"禁止原因: {'; '.join(tl.prohibition_reasons) if tl.prohibition_reasons else '无'}\n"
        f"限制原因: {'; '.join(tl.restriction_reasons) if tl.restriction_reasons else '无'}\n"
        f"缺失安全措施: {', '.join(tl.missing_security_measures) if tl.missing_security_measures else '无'}"
    )

    # Risk matrix block
    matrix_rows = []
    for row in rule_result.risk_matrix:
        matrix_rows.append(
            f"- {row.entity_name} x {row.data_item_name} = {row.traffic_light} "
            f"({row.covered_person_status}, threshold_hit={row.threshold_hit})"
        )
    matrix_block = "\n".join(matrix_rows) if matrix_rows else "- 无匹配项"

    return (
        f"【EO 14117 上下文包】\n"
        f"- module_key: {context_pack.module_key}\n"
        f"- request_id: {context_pack.request_id}\n"
        f"- chapter_id: {chapter_id}\n"
        f"- company_name: {payload.company_name}\n"
        f"- transaction_type: {payload.transaction_type}\n"
        f"- transaction_description: {payload.transaction_description}\n"
        f"\n【红黄绿判定结果】\n{tl_block}\n"
        f"\n【风险矩阵】\n{matrix_block}\n"
        f"\n【事实】\n"
        + "\n".join(
            f"- {fact.field_path}: {fact.normalized_value}"
            for fact in context_pack.facts[:15]
        )
        + "\n\n【法规】\n"
        + reg_block
        + "\n\n【问题】\n"
        + issue_block
        + "\n\n【证据】\n"
        + evidence_block
    )


def _render_placeholder_chapter(
    title: str,
    chapter_id: str,
    rule_result: US14117RuleEngineResult,
) -> str:
    """Render a structured placeholder when LLM is disabled."""
    tl = rule_result.traffic_light
    tc = rule_result.transaction_classification

    if chapter_id == "overall_conclusion":
        light_label = {"RED": "红灯（禁止传输）", "YELLOW": "黄灯（限制性交易）", "GREEN": "绿灯（低风险放行）"}
        yellow_note = ""
        if tl.yellow_status == "blocked":
            yellow_note = "\n> **⚠️ 整改前不得推进数据传输。** 存在安全措施缺口，在全部整改完成并经法务审批前，不得继续推进。\n"
        elif tl.yellow_status == "controlled":
            yellow_note = "\n> **✅ 安全措施已基本落实，可在持续监控和季度审计下推进。**\n"

        return (
            f"## 总体结论\n\n"
            f"**红黄绿判定: {light_label.get(tl.overall_light, tl.overall_light)}**\n\n"
            f"{tl.summary}\n"
            f"{yellow_note}\n"
            f"### 传输可行性\n\n"
            f"{'禁止传输' if tl.is_prohibited else '限制性交易，需采取措施' if tl.is_restricted else '当前可传输，建议持续监控'}\n\n"
            f"{'可条件性推进: 是' if tl.can_proceed_conditionally else '可条件性推进: 否'}\n\n"
            f"### 触发规则\n\n"
            + ("".join(f"- {r}\n" for r in tl.prohibition_reasons))
            + ("".join(f"- {r}\n" for r in tl.restriction_reasons))
            + ("\n### 需补充材料\n\n" + "".join(f"- {q}\n" for q in tl.clarification_questions) if tl.clarification_questions else "")
        )

    elif chapter_id == "risk_details":
        lines = ["## 风险详情与分析\n"]
        # Group entities by status
        confirmed = [ea for ea in rule_result.entity_assessments if ea.get("covered_person_status") == "confirmed"]
        inferred = [ea for ea in rule_result.entity_assessments if ea.get("covered_person_status") == "inferred"]
        needs_review = [ea for ea in rule_result.entity_assessments if ea.get("covered_person_status") == "needs_review"]

        lines.append("### 涵盖人员/实体清单\n")
        if confirmed:
            lines.append("**已确认涵盖人员:**")
            for ea in confirmed:
                lines.append(f"- **{ea['entity_name']}** (置信度: {ea.get('confidence', 0):.0%}): {'; '.join(ea.get('covered_person_reasons', []))}")
        if inferred:
            lines.append("\n**推断为涵盖人员 (需法务确认):**")
            for ea in inferred:
                lines.append(f"- **{ea['entity_name']}** (置信度: {ea.get('confidence', 0):.0%}): {'; '.join(ea.get('covered_person_reasons', []))}")
        if needs_review:
            lines.append("\n**需进一步尽调:**")
            for ea in needs_review:
                lines.append(f"- **{ea['entity_name']}**: {'; '.join(ea.get('covered_person_reasons', ['信息不足']))}")
                for info in ea.get("missing_information", [])[:2]:
                    lines.append(f"  - 缺失信息: {info}")

        lines.append("\n### 敏感数据分布\n")
        for dc in rule_result.data_classifications:
            lines.append(
                f"- **{dc['data_item_name']}**: {dc['doj_category']}, "
                f"US persons: {dc['us_person_count']}, "
                f"阈值: {dc['bulk_threshold']}, "
                f"命中: {'是' if dc['threshold_hit'] else '否'}"
                f"{' (低置信度⚠️)' if dc.get('confidence', 1.0) < 0.75 else ''}"
            )
        lines.append("\n### 风险匹配矩阵\n")
        for row in rule_result.risk_matrix:
            lines.append(
                f"- {row.entity_name} [{row.covered_person_status}] × {row.data_item_name} → **{row.traffic_light}** "
                f"({row.reason})"
            )
        return "\n".join(lines)

    elif chapter_id == "compliance_actions":
        lines = ["## 合规措施建议与行动清单\n"]
        if tl.overall_light == "RED":
            lines.append("### 红灯措施\n- 立即停止数据传输\n- 咨询法务团队\n- 评估替代方案（如本地化处理、非涵盖人员传输等）\n- 如需继续，评估是否可能通过调整交易结构改变法律定性")
        elif tl.overall_light == "YELLOW":
            if tl.yellow_status == "blocked":
                lines.append("### ⚠️ 黄灯（整改前禁止推进）\n")
                lines.append("**在以下安全措施全部整改完成前，不得继续推进数据传输。**\n")
            else:
                lines.append("### ✅ 黄灯（条件满足可推进）\n")
                lines.append("**安全措施已基本落实，可在持续监控下推进。**\n")
            lines.append("\n### 必要安全措施状态\n")
            for measure in tl.required_security_measures:
                if measure in tl.missing_security_measures:
                    lines.append(f"- ❌ **缺失**: {measure}")
                else:
                    lines.append(f"- ✅ 已具备: {measure}")
            if tl.missing_security_measures:
                lines.append(f"\n**缺失措施 ({len(tl.missing_security_measures)}项)**: {', '.join(tl.missing_security_measures)}")
                lines.append("\n建议90天内完成整改，整改完成后重新提交评估。")
            if tl.can_proceed_conditionally:
                lines.append("\n### 持续合规要求\n- 保持季度独立审计\n- 维持访问日志至少1年\n- 供应商合同包含再传输限制和审计权\n- 接收方变更时重新评估\n- 法规更新时及时调整措施")
        else:
            lines.append("### 绿灯措施\n- 保持当前合规状态\n- 建立季度复审机制\n- 监控法规更新和接收方变化\n- 禁止未经审批的再转让\n- 更新数据清单和人数统计")
        return "\n".join(lines)

    elif chapter_id == "attachments_monitoring":
        lines = [
            "## 附件与持续监控\n\n"
            "### 附件清单\n"
            "（详见输出包中的 rule_engine_result.json、facts.json、evidence_chain.json）\n"
        ]
        if tl.clarification_questions:
            lines.append("\n### ⚠️ 需补充材料\n")
            for q in tl.clarification_questions:
                lines.append(f"- {q}")
        lines.append("\n### 持续监控建议\n"
            "- 季度复审接收方实体状态\n"
            "- 监控 EO 14117 法规更新\n"
            "- 定期审计安全措施有效性\n"
            "- 更新数据清单和人数统计\n"
            "- 接收方变更、数据类别新增、交易结构调整时触发重新评估"
        )
        return "\n".join(lines)

    return f"（{title}：占位内容）"


def _build_template_mapping(
    payload: US14117Request,
    chapters: list[US14117Chapter],
    rule_result: US14117RuleEngineResult,
) -> dict[str, str]:
    """Build template variable mapping for MD/DOCX rendering."""
    def pick(no: int) -> str:
        for chapter in chapters:
            if chapter.chapter_no == no:
                return chapter.content
        return ""

    tl = rule_result.traffic_light
    light_label = {"RED": "红灯（禁止传输）", "YELLOW": "黄灯（限制性交易）", "GREEN": "绿灯（低风险放行）"}
    yellow_label = {"blocked": "整改前禁止推进", "controlled": "条件满足可推进", "": ""}

    citations: list[str] = []
    for chapter in chapters:
        if chapter.citations:
            citations = chapter.citations
            break

    # Build covered entity list with tri-state
    confirmed_entities = [
        ea["entity_name"] for ea in rule_result.entity_assessments
        if ea.get("covered_person_status") == "confirmed"
    ]
    inferred_entities = [
        ea["entity_name"] for ea in rule_result.entity_assessments
        if ea.get("covered_person_status") == "inferred"
    ]
    needs_review_entities = [
        ea["entity_name"] for ea in rule_result.entity_assessments
        if ea.get("covered_person_status") == "needs_review"
    ]
    entity_parts = []
    if confirmed_entities:
        entity_parts.append("**已确认涵盖人员:**\n" + "\n".join(f"- {e}" for e in confirmed_entities))
    if inferred_entities:
        entity_parts.append("**推断为涵盖人员:**\n" + "\n".join(f"- {e}" for e in inferred_entities))
    if needs_review_entities:
        entity_parts.append("**需进一步尽调:**\n" + "\n".join(f"- {e}" for e in needs_review_entities))
    if not entity_parts:
        entity_parts.append("- 未发现涵盖人员/实体")
    entity_block = "\n\n".join(entity_parts)

    # Build data classification summary
    data_lines = []
    for dc in rule_result.data_classifications:
        data_lines.append(
            f"- {dc['data_item_name']}: {dc['doj_category']} "
            f"(US persons: {dc['us_person_count']}, threshold: {dc['bulk_threshold']}, "
            f"hit: {'Y' if dc['threshold_hit'] else 'N'})"
        )
    data_block = "\n".join(data_lines) if data_lines else "- 未提供数据分类"

    # Build risk matrix markdown table
    if rule_result.risk_matrix:
        matrix_lines = ["| Entity | Data Item | Category | US Persons | Threshold | Hit | Traffic Light |",
                        "|--------|-----------|----------|------------|-----------|-----|---------------|"]
        for row in rule_result.risk_matrix:
            matrix_lines.append(
                f"| {row.entity_name} | {row.data_item_name} | {row.data_category} | "
                f"{row.us_person_count} | {row.threshold} | {row.threshold_hit} | {row.traffic_light} |"
            )
        matrix_block = "\n".join(matrix_lines)
    else:
        matrix_block = "无匹配项"

    # Security gaps
    sec_gap = rule_result.security_gap_report
    missing_block = "\n".join(f"- {m}" for m in sec_gap.get("missing", [])) if sec_gap.get("missing") else "- 无缺失"

    mapping = {
        "overall_conclusion": attach_citations(
            summarize_for_slot(pick(1), max_sentences=4, max_chars=500),
            citations,
        ),
        "traffic_light_label": light_label.get(tl.overall_light, tl.overall_light),
        "traffic_light_summary": tl.summary,
        "is_prohibited": "是" if tl.is_prohibited else "否",
        "is_restricted": "是" if tl.is_restricted else "否",
        "prohibition_reasons": "\n".join(f"- {r}" for r in tl.prohibition_reasons) or "无",
        "restriction_reasons": "\n".join(f"- {r}" for r in tl.restriction_reasons) or "无",
        "covered_entity_list": entity_block,
        "data_classification_summary": attach_citations(data_block, citations),
        "risk_matrix_table": matrix_block,
        "security_gaps": missing_block,
        "required_measures": "\n".join(f"- {m}" for m in tl.required_security_measures) or "无",
        "yellow_status": yellow_label.get(tl.yellow_status, tl.yellow_status),
        "can_proceed": "是（条件满足，可在持续监控下推进）" if tl.can_proceed_conditionally else "否（存在安全措施缺口）",
        "clarification_questions": "\n".join(f"- {q}" for q in tl.clarification_questions) if tl.clarification_questions else "无",
        "covered_entity_detail": entity_block,
        "risk_details": attach_citations(
            summarize_for_slot(pick(2), max_sentences=4, max_chars=500),
            citations,
        ),
        "compliance_actions": attach_citations(
            summarize_for_slot(pick(3), max_sentences=4, max_chars=500),
            citations,
        ),
        "attachments_monitoring": attach_citations(
            summarize_for_slot(pick(4), max_sentences=3, max_chars=400),
            citations,
        ),
    }
    return mapping


def _render_markdown_fallback(
    output_path: Path,
    payload: US14117Request,
    chapters: list[US14117Chapter],
    rule_result: US14117RuleEngineResult,
    date_stamp: str,
) -> None:
    """Render markdown report when no template file exists."""
    tl = rule_result.traffic_light
    light_label = {"RED": "红灯（禁止传输）", "YELLOW": "黄灯（限制性交易）", "GREEN": "绿灯（低风险放行）"}

    lines = [
        f"# EO 14117 风险评估结论报告 — {payload.company_name}",
        f"**生成日期**: {date_stamp}",
        f"**项目**: {payload.project_name}",
        f"**交易类型**: {payload.transaction_type}",
        "",
        f"## 总体结论",
        f"**红黄绿判定: {light_label.get(tl.overall_light, tl.overall_light)}**",
        "",
        tl.summary,
        "",
        "---",
    ]

    for chapter in chapters:
        lines.append(f"## {chapter.title}")
        lines.append("")
        lines.append(chapter.content)
        lines.append("")
        if chapter.citations:
            lines.append(f"*引用法规: {'; '.join(chapter.citations)}*")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
