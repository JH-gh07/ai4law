from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.artifacts import bundle_files, render_pdf_report, render_simple_xlsx
from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder
from backend.common.workflow import GenerationContextPack, WorkflowPipeline
from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.common.render.summary import attach_citations, summarize_for_slot
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.cn_flow.evidence_builder import build_cn_flow_evidence
from backend.modules.cn_flow.fact_builder import build_cn_flow_facts
from backend.modules.cn_flow.issue_builder import CN_FLOW_CHAPTER_KEYS, build_cn_flow_issues
from backend.modules.cn_flow.schema import (
    CNFlowAsyncAccepted,
    CNFlowAsyncStatus,
    CNFlowChapter,
    CNFlowRequest,
    CNFlowResult,
    CNFlowRiskItem,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/4.1_cn_flow_compliance_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/4.1_cn_flow_compliance_template_v0.md")


CN_FLOW_CHAPTERS = [
    "场景定义与适用范围",
    "数据类型与实体结构分析",
    "限制条件命中分析",
    "风险分级与处置建议",
]


class CNFlowService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="cn_flow")

    def generate_report(self, payload: CNFlowRequest) -> CNFlowResult:
        task_id = str(uuid.uuid4())
        trace_dir = Path("outputs/cn_flow") / task_id / "trace"
        trace = TraceRecorder(trace_dir)
        token = current_trace.set(trace)
        try:
            run_result = self._build_pipeline().run(payload=payload, task_id=task_id, trace=trace)
        finally:
            current_trace.reset(token)
        return CNFlowResult(
            report_path=run_result.outputs["docx"],
            output_files=run_result.outputs,
            company_name=payload.company_name,
            risk_level=run_result.diagnosis.risk_level,
            risk_items=run_result.diagnosis.risk_items,
            chapters=run_result.chapters,
            consistency_issues=run_result.consistency_issues,
            attachment_notes=[
                f"{item.get('source_ref', '')}: {item.get('summary', '')}"
                for item in run_result.context_pack.attachment_notes
            ],
        )

    def _build_pipeline(self) -> WorkflowPipeline:
        return WorkflowPipeline(
            extract_profile=lambda payload: payload,
            evaluate_diagnosis=self._evaluate_diagnosis,
            validate_path=lambda payload, path, rationale: None,
            build_facts=self._build_facts,
            retrieve_regulations=self._retrieve_regulations,
            build_attachment_notes=self._extract_attachment_notes,
            build_issues=self._build_issues,
            build_evidence=self._build_evidence,
            build_context_pack=self._build_context_pack,
            generate_chapters=self._generate_chapters_from_pack,
            check_consistency=self._check_consistency_with_context,
            check_alignment=lambda content, profile: [],
            render_artifacts=self._render_outputs,
            request_event_name="cn_flow_request",
            consistency_check_labels=["cn_flow_rules", "context_pack_references"],
        )

    def _evaluate_diagnosis(self, payload: CNFlowRequest):
        risk_items = self._build_risk_items(payload)
        risk_level = self._resolve_overall_level(risk_items)
        diagnosis = _CNFlowDiagnosis(risk_level=risk_level, risk_items=risk_items)
        diagnosis.payload = payload
        return diagnosis

    def _build_facts(self, payload: CNFlowRequest, profile: CNFlowRequest, diagnosis: "_CNFlowDiagnosis"):
        return build_cn_flow_facts(payload, risk_level=diagnosis.risk_level, risk_items=diagnosis.risk_items)

    @staticmethod
    def _retrieve_regulations(_: CNFlowRequest) -> list[dict]:
        docs = retrieve_regulations(
            "EO 14117 US China data flow restricted transactions",
            top_k=4,
            jurisdiction="us",
            path="all",
        )
        return [
            {
                "source_id": item.id,
                "title": item.title,
                "article": item.article,
                "snippet": item.content,
            }
            for item in docs
        ]

    def _build_issues(
        self,
        facts,
        diagnosis: "_CNFlowDiagnosis",
        regulations: list[dict],
        attachment_notes: list[dict[str, str]],
    ):
        return build_cn_flow_issues(
            diagnosis.payload,
            facts,
            diagnosis.risk_items,
            regulations,
        )

    @staticmethod
    def _build_evidence(facts, issues, regulations, diagnosis: "_CNFlowDiagnosis"):
        return build_cn_flow_evidence(facts, issues, regulations)

    def _build_context_pack(
        self,
        *,
        task_id: str,
        diagnosis: "_CNFlowDiagnosis",
        facts,
        regulations,
        issues,
        evidence_chain,
        path_warning: str | None,
        attachment_notes: list[dict[str, str]],
    ) -> GenerationContextPack:
        return GenerationContextPack(
            module_key="cn_flow",
            request_id=task_id,
            facts=facts,
            diagnosis_result=diagnosis.model_dump(),
            regulations=regulations,
            issues=issues,
            evidence_chain=evidence_chain,
            path_warning=path_warning,
            risk_summary={"risk_level": diagnosis.risk_level},
            attachment_notes=attachment_notes,
            output_requirements={"chapter_keys": list(CN_FLOW_CHAPTER_KEYS.values())},
        )

    def _generate_chapters_from_pack(
        self,
        payload: CNFlowRequest,
        regulations: list[dict],
        context_pack: GenerationContextPack,
    ) -> list[CNFlowChapter]:
        citations = [f"{item.get('title', '')}{item.get('article', '')}" for item in regulations]
        chapters: list[CNFlowChapter] = []
        for idx, title in enumerate(CN_FLOW_CHAPTERS, start=1):
            chapter_id = CN_FLOW_CHAPTER_KEYS[title]
            context_block = self._build_context_block_from_pack(payload, context_pack, chapter_id)
            if self.llm_client and self.llm_client.enabled:
                content = generate_chapter(self.llm_client, "cn_flow", title, context_block, citations=citations)
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(
                CNFlowChapter(
                    chapter_no=idx,
                    title=title,
                    content=content,
                    citations=citations,
                    risk_level=context_pack.risk_summary.get("risk_level", "LOW") if context_pack.risk_summary else "LOW",
                )
            )
        return chapters

    def submit_async(self, payload: CNFlowRequest) -> CNFlowAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> CNFlowAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> CNFlowAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> CNFlowAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> CNFlowAsyncAccepted:
        return CNFlowAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> CNFlowAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = CNFlowResult.model_validate(snapshot.result)
        return CNFlowAsyncStatus(
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

    @staticmethod
    def _resolve_overall_level(items: list[CNFlowRiskItem]) -> str:
        levels = {item.risk_level for item in items}
        if "HIGH" in levels:
            return "HIGH"
        if "MEDIUM" in levels:
            return "MEDIUM"
        return "LOW"

    def _build_risk_items(self, payload: CNFlowRequest) -> list[CNFlowRiskItem]:
        items: list[CNFlowRiskItem] = []
        if payload.sensitive_data_flags:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R1",
                    risk_level="HIGH",
                    title="存在敏感数据跨境流动",
                    basis="EO 14117 敏感数据外流限制框架",
                    recommendation="优先评估敏感字段脱敏、最小化及本地化处理方案。",
                    affected_entities=[entity.entity_name for entity in payload.recipient_entities],
                )
            )
        restricted = [entity.entity_name for entity in payload.recipient_entities if entity.is_restricted_party]
        if restricted:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R2",
                    risk_level="HIGH",
                    title="接收方存在受限主体风险",
                    basis="受限交易与第三方尽调要求",
                    recommendation="暂停向受限主体传输，补齐尽调与审批记录。",
                    affected_entities=restricted,
                )
            )
        if "subprocessor" in payload.transfer_chain.lower() or "第三方" in payload.transfer_chain:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R3",
                    risk_level="MEDIUM",
                    title="传输链路复杂导致控制断点",
                    basis="跨实体/再传输控制要求",
                    recommendation="明确 onward transfer 约束与监控机制，补充链路审计。",
                    affected_entities=[entity.entity_name for entity in payload.recipient_entities],
                )
            )
        if not items:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R0",
                    risk_level="LOW",
                    title="暂未识别高风险触发条件",
                    basis="输入范围内未命中高风险规则",
                    recommendation="保持季度复审并持续监控接收方变化。",
                    affected_entities=[entity.entity_name for entity in payload.recipient_entities],
                )
            )
        return items

    def _extract_attachment_notes(self, payload: CNFlowRequest) -> list[dict[str, str]]:
        notes: list[dict[str, str]] = []
        for item in payload.attachments:
            try:
                text = self.parser.parse_text(item.storage_uri)
                notes.append(
                    {
                        "source_ref": item.file_name,
                        "summary": text[:160].replace(chr(10), " "),
                    }
                )
            except (FileNotFoundError, ValueError) as exc:
                notes.append(
                    {
                        "source_ref": item.file_name,
                        "summary": f"[parse skipped] {exc}",
                    }
                )
        return notes

    @staticmethod
    def _check_consistency_with_context(payload: CNFlowRequest, chapters: list[CNFlowChapter], context_pack: GenerationContextPack) -> list[str]:
        issues: list[str] = []
        required_roles = {item.file_role for item in payload.attachments}
        if "data_inventory" not in required_roles:
            issues.append("Missing required attachment role: data_inventory")
        if "entity_inventory" not in required_roles:
            issues.append("Missing required attachment role: entity_inventory")
        if any(item.severity in {"HIGH", "BLOCKER"} for item in context_pack.issues):
            issues.append("Contains HIGH risk items; recommend legal escalation before execution.")
        if any(not chapter.citations for chapter in chapters):
            issues.append("Some chapters have no citation.")
        return issues

    def _render_outputs(
        self,
        *,
        task_id: str,
        payload: CNFlowRequest,
        profile: CNFlowRequest,
        regulations: list[dict],
        chapters: list[CNFlowChapter],
        path_warning: str | None,
        alignment_warning: str | None,
        issues,
        evidence_chain,
        attachment_notes: list[dict[str, str]],
        trace_manifest_path: str,
        facts,
        diagnosis: "_CNFlowDiagnosis",
    ) -> dict[str, str]:
        sections: list[tuple[str, str]] = [
            ("输入摘要", payload.model_dump_json(indent=2)),
            ("风险清单摘要", "\n".join(f"- {item.risk_id}: {item.title}" for item in diagnosis.risk_items)),
            (
                "附件解析摘要",
                "\n".join(f"- {item.get('source_ref', '')}: {item.get('summary', '')}" for item in attachment_notes) or "- 无",
            ),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

        output_dir = Path("outputs/cn_flow") / task_id / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        date_stamp = format_date_stamp()
        base = safe_filename(payload.company_name)
        md_output = output_dir / f"{base}_14117_风险评估结论报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{base}_14117_风险评估结论报告_草案_{date_stamp}.docx"
        pdf_output = output_dir / f"{base}_14117_风险评估结论报告_草案_{date_stamp}.pdf"
        xlsx_output = output_dir / f"{base}_14117_风险清单_草案_{date_stamp}.xlsx"
        zip_output = output_dir / f"{base}_14117_输出包_草案_{date_stamp}.zip"

        mapping = _build_template_mapping(payload, chapters, diagnosis.risk_items)
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        render_pdf_report(pdf_output, "对华数据流动合规报告（草案）", sections)
        headers = ["risk_id", "risk_level", "title", "basis", "recommendation", "affected_entities"]
        rows = [
            [
                item.risk_id,
                item.risk_level,
                item.title,
                item.basis,
                item.recommendation,
                "; ".join(item.affected_entities),
            ]
            for item in diagnosis.risk_items
        ]
        render_simple_xlsx(xlsx_output, headers=headers, rows=rows)
        issue_json = output_dir / "issue_list.json"
        issue_json.write_text(json.dumps([item.model_dump() for item in issues], ensure_ascii=False, indent=2), encoding="utf-8")
        evidence_json = output_dir / "evidence_chain.json"
        evidence_json.write_text(
            json.dumps([item.model_dump() for item in evidence_chain], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        facts_json = output_dir / "facts.json"
        facts_json.write_text(json.dumps([item.model_dump() for item in facts], ensure_ascii=False, indent=2), encoding="utf-8")
        trace_manifest = output_dir / "trace_manifest.json"
        trace_manifest.write_text(Path(trace_manifest_path).read_text(encoding="utf-8"), encoding="utf-8")
        bundle_files(
            zip_output,
            [docx_output, md_output, pdf_output, xlsx_output, issue_json, evidence_json, facts_json, trace_manifest],
        )
        return {
            "markdown": str(md_output),
            "docx": str(docx_output),
            "pdf": str(pdf_output),
            "xlsx": str(xlsx_output),
            "zip": str(zip_output),
            "issue_list_json": str(issue_json),
            "evidence_chain_json": str(evidence_json),
            "facts_json": str(facts_json),
            "trace_manifest": str(trace_manifest),
        }

    @staticmethod
    def _build_context_block_from_pack(
        payload: CNFlowRequest,
        context_pack: GenerationContextPack,
        chapter_id: str,
    ) -> str:
        matched_issues = [item for item in context_pack.issues if chapter_id in item.affects_outputs]
        if not matched_issues:
            matched_issues = [item for item in context_pack.issues if item.severity in {"HIGH", "BLOCKER"}]
        issue_block = "\n".join(
            f"- {item.issue_id} | {item.severity} | {item.title} | {item.recommended_action}"
            for item in matched_issues
        ) or "- 无"
        reg_block = "\n".join(
            f"- {item.get('source_id', 'unknown')} | {item.get('title', '')}{item.get('article', '')}: {str(item.get('snippet', ''))[:120]}"
            for item in context_pack.regulations[:5]
        ) or "- 无"
        evidence_block = "\n".join(
            f"- {item.evidence_id} | {item.claim} -> {item.conclusion}"
            for item in context_pack.evidence_chain
        ) or "- 无"
        return (
            f"【上下文包】\n"
            f"- module_key: {context_pack.module_key}\n"
            f"- request_id: {context_pack.request_id}\n"
            f"- chapter_id: {chapter_id}\n"
            f"- company_name: {payload.company_name}\n"
            f"- transfer_purpose: {payload.transfer_purpose}\n"
            f"- risk_level: {(context_pack.risk_summary or {}).get('risk_level', 'LOW')}\n"
            f"\n【事实】\n"
            + "\n".join(f"- {fact.field_path}: {fact.normalized_value}" for fact in context_pack.facts[:12])
            + "\n\n【法规】\n"
            + reg_block
            + "\n\n【问题】\n"
            + issue_block
            + "\n\n【证据】\n"
            + evidence_block
        )


class _CNFlowDiagnosis:
    def __init__(self, *, risk_level: str, risk_items: list[CNFlowRiskItem]) -> None:
        self.risk_level = risk_level
        self.risk_items = risk_items
        self.recommended_path = "cn_flow"
        self.rationale = "Rule-based CN flow risk aggregation"
        self.payload: CNFlowRequest | None = None

    def model_dump(self) -> dict:
        return {
            "risk_level": self.risk_level,
            "recommended_path": self.recommended_path,
            "rationale": self.rationale,
            "risk_items": [item.model_dump() for item in self.risk_items],
        }


def _build_template_mapping(
    payload: CNFlowRequest,
    chapters: list[CNFlowChapter],
    risk_items: list[CNFlowRiskItem],
) -> dict[str, str]:
    def pick(no: int) -> str:
        for chapter in chapters:
            if chapter.chapter_no == no:
                return chapter.content
        return ""

    def overall_level(items: list[CNFlowRiskItem]) -> str:
        levels = {item.risk_level for item in items}
        if "HIGH" in levels:
            return "HIGH"
        if "MEDIUM" in levels:
            return "MEDIUM"
        return "LOW"

    level = overall_level(risk_items)
    color_map = {
        "HIGH": "红灯（禁止/高度受限）",
        "MEDIUM": "黄灯（受限需措施）",
        "LOW": "绿灯（低风险放行）",
    }
    high_entities = [e.entity_name for e in payload.recipient_entities if e.is_restricted_party]
    citations: list[str] = []
    for chapter in chapters:
        if chapter.citations:
            citations = chapter.citations
            break

    matrix = _build_risk_matrix(payload, level)
    rating_block = "\n".join(
        [
            f"总体结论：{color_map.get(level, level)}",
            "",
            "高风险实体清单：",
            "- " + ("\n- ".join(high_entities) if high_entities else "未发现受限实体"),
            "",
            "风险矩阵（实体 x 数据类别）：",
            matrix,
        ]
    )
    rating_block = attach_citations(rating_block, citations)

    entity_screening = "\n".join(
        f"- {entity.entity_name} | {entity.country_region} | {entity.entity_role} | 受限主体={entity.is_restricted_party}"
        for entity in payload.recipient_entities
    )

    return {
        "business_overview": attach_citations(
            summarize_for_slot(pick(1), max_sentences=3, max_chars=360),
            citations,
        ),
        "data_inventory_analysis": attach_citations(
            summarize_for_slot(pick(2), max_sentences=3, max_chars=360),
            citations,
        ),
        "entity_screening": entity_screening or "未提供实体清单。",
        "risk_rating": rating_block,
        "mitigation_and_actions": attach_citations(
            summarize_for_slot(pick(4), max_sentences=3, max_chars=360),
            citations,
        ),
    }


def _build_risk_matrix(payload: CNFlowRequest, level: str) -> str:
    categories = payload.data_categories + payload.sensitive_data_flags
    headers = ["实体/数据"] + categories
    rows = []
    for entity in payload.recipient_entities:
        row = [entity.entity_name]
        for cat in categories:
            if cat in payload.sensitive_data_flags:
                row.append("HIGH" if level == "HIGH" else "MEDIUM")
            else:
                row.append("MEDIUM" if level in {"HIGH", "MEDIUM"} else "LOW")
        rows.append(row)

    def as_row(cells: list[str]) -> str:
        return "| " + " | ".join(cells) + " |"

    lines = [as_row(headers), as_row(["---"] * len(headers))]
    lines.extend(as_row(row) for row in rows)
    return "\n".join(lines)
