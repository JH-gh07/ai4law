from __future__ import annotations

import csv
import json
from pathlib import Path

from backend.common.knowledge.registry import ROOT, ensure_source_registry
from backend.common.knowledge.v2 import KnowledgeChunkV2
from backend.services.review_service.rulebook_loader import RulebookLoader

SOURCES_CSV = ROOT / "doc" / "knowledge" / "index" / "sources.csv"
NORMALIZED_JSONL = ROOT / "doc" / "knowledge" / "normalized" / "regulation_articles.jsonl"
OFFICIAL_TEMPLATE_SCHEMA = ROOT / "backend" / "modules" / "assessment" / "templates" / "official_template_schema.json"
OFFICIAL_TEMPLATE_MD = ROOT / "backend" / "modules" / "assessment" / "templates" / "official_risk_self_assessment_template.md"


def _load_source_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if not SOURCES_CSV.exists():
        return rows
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows[(row.get("source_id") or "").strip()] = {k: (v or "").strip() for k, v in row.items()}
    return rows


def _authority_level(title: str) -> str:
    clean = (title or "").replace("《", "").replace("》", "")
    if "法" in clean and "办法" not in clean:
        return "high"
    if any(token in clean for token in ("办法", "条例", "规定")):
        return "medium"
    return "low"


def _binding_force(title: str) -> str:
    clean = (title or "").replace("《", "").replace("》", "")
    if "法" in clean and "办法" not in clean:
        return "mandatory"
    if any(token in clean for token in ("办法", "条例", "规定")):
        return "mandatory"
    if any(token in clean for token in ("指南", "标准", "规范")):
        return "recommended"
    return "reference"


def build_legal_chunks_cn() -> list[KnowledgeChunkV2]:
    registry = {item.source_id: item for item in ensure_source_registry()}
    source_rows = _load_source_rows()
    chunks: list[KnowledgeChunkV2] = []
    if not NORMALIZED_JSONL.exists():
        return chunks

    with NORMALIZED_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if (row.get("jurisdiction") or "").strip().lower() != "cn":
                continue
            source_id = str(row.get("source_id") or "")
            registry_entry = registry.get(source_id)
            source_row = source_rows.get(source_id, {})
            title = str(row.get("law_name") or source_row.get("title") or "")
            path = str(row.get("path") or source_row.get("path") or "all")
            modules = []
            if registry_entry is not None:
                modules = list(registry_entry.modules)
            elif path in {"assessment", "all"}:
                modules.append("cn_assessment")
            elif path in {"review", "all", "scc"}:
                modules.append("cn_review")
            else:
                modules.append("cn_diagnosis")
            module = "cn_diagnosis"
            if "cn_assessment" in modules:
                module = "cn_assessment"
            elif "cn_review" in modules:
                module = "cn_review"

            source_kind = registry_entry.source_kind if registry_entry is not None else "law_article"
            allowed_usage = list(registry_entry.allowed_usage) if registry_entry is not None else ["legal_grounding", "external_report", "internal_review"]
            chunks.append(
                KnowledgeChunkV2(
                    chunk_id=str(row.get("article_id") or ""),
                    source_id=source_id,
                    title=title,
                    content=str(row.get("content") or ""),
                    layer="L1_regulatory_evidence",
                    template_type="none",
                    source_kind=str(source_kind),
                    module=module,
                    jurisdiction="cn",
                    doc_type=str(row.get("doc_type") or source_row.get("doc_type") or "law"),
                    authority_level=registry_entry.authority_level if registry_entry is not None else _authority_level(title),
                    binding_force=registry_entry.binding_force if registry_entry is not None else _binding_force(title),
                    allowed_usage=allowed_usage,
                    can_be_cited=True,
                    can_enter_external_report=True,
                    reference_ids=[],
                    citation_anchor=str(row.get("article_ref") or ""),
                    scenario_tags=[path],
                    chunk_strategy="article_split",
                    article_no=str(row.get("article_ref") or ""),
                    path=path,
                    source_url=str(row.get("source_url") or source_row.get("url") or ""),
                    snapshot_path=str(row.get("snapshot_path") or source_row.get("snapshot_path") or ""),
                    keywords=[str(item) for item in row.get("keywords", [])],
                    structured_payload={
                        "status": str(row.get("status") or source_row.get("status") or "effective"),
                        "publish_date": str(row.get("publish_date") or ""),
                        "effective_date": str(row.get("effective_date") or ""),
                    },
                )
            )
    return chunks


def build_workflow_chunks_cn() -> list[KnowledgeChunkV2]:
    rows = [
        {
            "chunk_id": "WF-CN-DIAG-CIIO",
            "source_id": "WF-CN-DIAGNOSIS",
            "title": "CIIO 触发安全评估",
            "content": "如果数据处理者属于关键信息基础设施运营者，则个人信息或重要数据出境应优先进入安全评估路径。",
            "module": "cn_diagnosis",
            "reference_ids": ["CN-REG-004", "CN-LAW-003"],
            "scenario_tags": ["assessment", "path_diagnosis"],
            "structured_payload": {
                "rule_name": "ciio_security_assessment",
                "input_signals": ["is_ciio"],
                "condition": "is_ciio == true",
                "output_action": "security_assessment",
            },
        },
        {
            "chunk_id": "WF-CN-DIAG-IMPORTANT-DATA",
            "source_id": "WF-CN-DIAGNOSIS",
            "title": "重要数据触发安全评估",
            "content": "如果出境数据包含重要数据，则应进入安全评估路径。",
            "module": "cn_diagnosis",
            "reference_ids": ["CN-REG-004", "CN-LAW-002"],
            "scenario_tags": ["assessment", "path_diagnosis"],
            "structured_payload": {
                "rule_name": "important_data_security_assessment",
                "input_signals": ["contains_important_data"],
                "condition": "contains_important_data == true",
                "output_action": "security_assessment",
            },
        },
        {
            "chunk_id": "WF-CN-DIAG-PII-THRESHOLD",
            "source_id": "WF-CN-DIAGNOSIS",
            "title": "个人信息数量阈值判断",
            "content": "如果累计向境外提供普通个人信息达到一百万人以上，建议进入安全评估路径。",
            "module": "cn_diagnosis",
            "reference_ids": ["CN-REG-004", "CN-LAW-003"],
            "scenario_tags": ["assessment", "path_diagnosis"],
            "structured_payload": {
                "rule_name": "pii_threshold_security_assessment",
                "input_signals": ["pii_count"],
                "condition": "pii_count >= 1000000",
                "output_action": "security_assessment",
            },
        },
        {
            "chunk_id": "WF-CN-ASSESS-MATERIALS",
            "source_id": "WF-CN-ASSESSMENT",
            "title": "安全评估申报材料清单",
            "content": "安全评估至少应准备自评估报告、申报书、法律文件摘要、接收方安全能力证明和必要性说明。",
            "module": "cn_assessment",
            "reference_ids": ["CN-GUIDE-009", "CN-REG-004"],
            "scenario_tags": ["assessment", "issue_discovery"],
            "structured_payload": {
                "rule_name": "assessment_materials_checklist",
                "output_action": "material_checklist",
                "required_materials": ["self_assessment_report", "filing_form", "legal_document_summary", "recipient_security_evidence", "necessity_statement"],
            },
        },
        {
            "chunk_id": "WF-CN-ASSESS-LEGAL-DOC",
            "source_id": "WF-CN-ASSESSMENT",
            "title": "法律文件重点核查项",
            "content": "安全评估中的法律文件应覆盖再转移约束、保存期限、违约责任、争议解决、个人权利保障等核心义务。",
            "module": "cn_assessment",
            "reference_ids": ["CN-REG-004", "CN-LAW-003"],
            "scenario_tags": ["assessment", "issue_discovery", "legal_document"],
            "structured_payload": {
                "rule_name": "assessment_legal_document_core_terms",
                "output_action": "issue_discovery",
                "required_terms": ["onward_transfer", "retention", "liability", "dispute_resolution", "data_subject_rights"],
            },
        },
        {
            "chunk_id": "WF-CN-REVIEW-PRIVACY",
            "source_id": "WF-CN-REVIEW",
            "title": "隐私政策高风险核查框架",
            "content": "隐私政策重点核查告知同意、境外接收方信息、撤回机制、权利响应期限、敏感个人信息保护和出境合法机制。",
            "module": "cn_review",
            "reference_ids": ["CN-LAW-003"],
            "scenario_tags": ["review", "issue_discovery", "privacy_policy"],
            "structured_payload": {
                "rule_name": "privacy_policy_review_focus",
                "document_type": "privacy_policy",
                "required_topics": ["consent_notice", "cross_border_transfer", "rights_request", "sensitive_pi"],
            },
        },
        {
            "chunk_id": "WF-CN-REVIEW-DPA",
            "source_id": "WF-CN-REVIEW",
            "title": "委托处理协议高风险核查框架",
            "content": "委托处理协议重点核查处理范围、出境责任分配、安全措施、删除返还证明和标准合同优先级冲突。",
            "module": "cn_review",
            "reference_ids": ["CN-LAW-003", "CN-REG-005"],
            "scenario_tags": ["review", "issue_discovery", "dpa"],
            "structured_payload": {
                "rule_name": "dpa_review_focus",
                "document_type": "dpa",
                "required_topics": ["processing_scope", "compliance_responsibility", "security_measure", "deletion_proof", "scc_priority"],
            },
        },
    ]
    chunks: list[KnowledgeChunkV2] = []
    for row in rows:
        chunks.append(
            KnowledgeChunkV2(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                title=row["title"],
                content=row["content"],
                layer="L2_business_rule",
                template_type="none",
                source_kind="workflow_rule",
                module=row["module"],
                jurisdiction="cn",
                doc_type="workflow_rule",
                authority_level="low",
                binding_force="reference",
                allowed_usage=["internal_review", "risk_explanation"],
                can_be_cited=False,
                can_enter_external_report=False,
                reference_ids=list(row["reference_ids"]),
                citation_anchor=row["title"],
                scenario_tags=list(row["scenario_tags"]),
                chunk_strategy="workflow_step",
                path="assessment" if "assessment" in row["scenario_tags"] else "review",
                structured_payload=dict(row["structured_payload"]),
            )
        )
    return chunks


def build_template_chunks_cn() -> list[KnowledgeChunkV2]:
    chunks: list[KnowledgeChunkV2] = []
    if OFFICIAL_TEMPLATE_SCHEMA.exists():
        schema = json.loads(OFFICIAL_TEMPLATE_SCHEMA.read_text(encoding="utf-8"))
        for section in schema.get("sections", []):
            chunks.append(
                KnowledgeChunkV2(
                    chunk_id=f"TPL-ASSESS-{section['section_id']}",
                    source_id="CN-TEMPLATE-ASSESSMENT-OFFICIAL",
                    title=section["title"],
                    content=section.get("description") or section["title"],
                    layer="L4_template",
                    template_type="official_template",
                    source_kind="template_slot",
                    module="cn_assessment",
                    jurisdiction="cn",
                    doc_type="official_template",
                    authority_level="medium",
                    binding_force="mandatory",
                    allowed_usage=["structure_control", "external_report"],
                    can_be_cited=False,
                    can_enter_external_report=False,
                    reference_ids=[],
                    citation_anchor=section["number"],
                    scenario_tags=["assessment", "official_template"],
                    chunk_strategy="template_slot",
                    path="assessment",
                    structured_payload={
                        "section_id": section["section_id"],
                        "number": section["number"],
                        "mapped_chapters": section.get("mapped_chapters", []),
                        "required_inputs": section.get("required_inputs", []),
                        "required_issues": section.get("required_issues", []),
                    },
                )
            )
            for subsection in section.get("subsections", []):
                chunks.append(
                    KnowledgeChunkV2(
                        chunk_id=f"TPL-ASSESS-{subsection['section_id']}",
                        source_id="CN-TEMPLATE-ASSESSMENT-OFFICIAL",
                        title=subsection["title"],
                        content=subsection.get("description") or subsection["title"],
                        layer="L4_template",
                        template_type="official_template",
                        source_kind="template_slot",
                        module="cn_assessment",
                        jurisdiction="cn",
                        doc_type="official_template",
                        authority_level="medium",
                        binding_force="mandatory",
                        allowed_usage=["structure_control", "external_report"],
                        can_be_cited=False,
                        can_enter_external_report=False,
                        reference_ids=[],
                        citation_anchor=subsection["number"],
                        scenario_tags=["assessment", "official_template"],
                        chunk_strategy="template_slot",
                        path="assessment",
                        structured_payload={
                            "section_id": subsection["section_id"],
                            "number": subsection["number"],
                            "mapped_chapters": subsection.get("mapped_chapters", []),
                            "required_inputs": subsection.get("required_inputs", []),
                            "required_issues": subsection.get("required_issues", []),
                        },
                    )
                )
    if OFFICIAL_TEMPLATE_MD.exists():
        text = OFFICIAL_TEMPLATE_MD.read_text(encoding="utf-8")
        chunks.append(
            KnowledgeChunkV2(
                chunk_id="TPL-ASSESS-EXAMPLE-MD",
                source_id="CN-TEMPLATE-ASSESSMENT-EXAMPLE",
                title="数据出境风险自评估报告示例文本",
                content=text[:1200],
                layer="L4_template",
                template_type="example",
                source_kind="template_slot",
                module="cn_assessment",
                jurisdiction="cn",
                doc_type="example_template",
                authority_level="low",
                binding_force="reference",
                allowed_usage=["internal_drafting"],
                can_be_cited=False,
                can_enter_external_report=False,
                reference_ids=[],
                citation_anchor="example_md",
                scenario_tags=["assessment", "example_template"],
                chunk_strategy="template_slot",
                path="assessment",
                structured_payload={"format": "markdown"},
            )
        )
    return chunks


def build_standard_clause_chunks_cn() -> list[KnowledgeChunkV2]:
    rulebook = RulebookLoader()
    rows = [
        {
            "chunk_id": "STD-CN-SCC-PRIORITY",
            "title": "标准合同优先性保护",
            "scenario_tags": ["scc_contract", "dpa", "other"],
            "clause_type": "CROSS_BORDER_TRANSFER",
            "content": "当标准合同正文与其他协议不一致时，不得约定由其他协议优先适用或削弱标准合同义务。",
            "protected_obligations": ["standard_contract_priority", "no_conflicting_master_agreement"],
            "reference_ids": ["CN-REG-005", "CN-LAW-003"],
            "modification_sensitivity": "high",
        },
        {
            "chunk_id": "STD-CN-SCC-RIGHTS",
            "title": "个人权利请求处理义务",
            "scenario_tags": ["scc_contract", "privacy_policy"],
            "clause_type": "RIGHTS_REQUEST",
            "content": "收到个人权利请求后，应及时响应，不得以笼统酌情或视情况为由无限期暂缓处理。",
            "protected_obligations": ["timely_response", "no_unbounded_delay", "rights_request_process"],
            "reference_ids": ["CN-LAW-003"],
            "modification_sensitivity": "high",
        },
        {
            "chunk_id": "STD-CN-SCC-LIABILITY",
            "title": "赔偿责任不得被不当限制",
            "scenario_tags": ["scc_contract", "dpa", "other"],
            "clause_type": "LIABILITY",
            "content": "涉及个人信息出境和受托处理的法律文件不应通过过低赔偿上限或全面免责削弱数据主体保护。",
            "protected_obligations": ["no_excessive_liability_cap", "no_full_exemption", "effective_remedy"],
            "reference_ids": ["CN-LAW-003", "CN-REG-004"],
            "modification_sensitivity": "high",
        },
        {
            "chunk_id": "STD-CN-DPA-DELETION",
            "title": "删除返还与证明机制",
            "scenario_tags": ["dpa", "other"],
            "clause_type": "RETENTION_DELETION",
            "content": "委托处理结束后，应明确删除或返还数据的时限、方式和完成证明。",
            "protected_obligations": ["delete_or_return", "completion_proof", "retention_limit"],
            "reference_ids": ["CN-LAW-003"],
            "modification_sensitivity": "medium",
        },
        {
            "chunk_id": "STD-CN-DPA-COMPLIANCE",
            "title": "出境合规责任不得整体转嫁",
            "scenario_tags": ["dpa", "other"],
            "clause_type": "CROSS_BORDER_TRANSFER",
            "content": "出境合规责任应由个人信息处理者主导，不宜整体约定由受托方单方完成安全评估或标准合同手续。",
            "protected_obligations": ["controller_primary_responsibility", "no_full_responsibility_shift"],
            "reference_ids": ["CN-LAW-003", "CN-REG-004", "CN-REG-005"],
            "modification_sensitivity": "high",
        },
    ]
    chunks: list[KnowledgeChunkV2] = []
    for row in rows:
        citation_strings = rulebook.get_citation_strings(row["clause_type"])
        chunks.append(
            KnowledgeChunkV2(
                chunk_id=row["chunk_id"],
                source_id=row["chunk_id"],
                title=row["title"],
                content=row["content"],
                layer="L1_regulatory_evidence",
                template_type="none",
                source_kind="standard_clause",
                module="cn_review",
                jurisdiction="cn",
                doc_type="standard_clause",
                authority_level="medium",
                binding_force="mandatory",
                allowed_usage=["legal_grounding", "external_report", "internal_review"],
                can_be_cited=True,
                can_enter_external_report=True,
                reference_ids=list(row["reference_ids"]),
                citation_anchor=row["title"],
                scenario_tags=list(row["scenario_tags"]),
                chunk_strategy="standard_clause",
                path="review",
                keywords=row["protected_obligations"],
                structured_payload={
                    "clause_no": row["chunk_id"],
                    "clause_title": row["title"],
                    "clause_type": row["clause_type"],
                    "protected_obligations": row["protected_obligations"],
                    "modification_sensitivity": row["modification_sensitivity"],
                    "citation_strings": citation_strings,
                },
            )
        )
    return chunks


def build_testcase_chunks_cn() -> list[KnowledgeChunkV2]:
    rows = [
        {
            "chunk_id": "TC-CN-ASSESS-001",
            "module": "cn_assessment",
            "title": "CIIO 安全评估案例",
            "content": "CIIO 向境外提供个人信息，需走安全评估路径，并准备自评估报告与接收方保障材料。",
            "structured_payload": {
                "expected_path": "assessment",
                "must_find_issues": ["ISSUE-ciio-security-assessment"],
                "must_cite_source_ids": ["CN-REG-004", "CN-LAW-003"],
            },
        },
        {
            "chunk_id": "TC-CN-ASSESS-002",
            "module": "cn_assessment",
            "title": "重要数据出境案例",
            "content": "涉及重要数据出境，应优先论证必要性、最小化和接收方安全能力。",
            "structured_payload": {
                "expected_path": "assessment",
                "must_find_issues": ["ISSUE-important-data"],
                "must_cite_source_ids": ["CN-LAW-002", "CN-REG-004"],
            },
        },
        {
            "chunk_id": "TC-CN-REVIEW-001",
            "module": "cn_review",
            "title": "标准合同优先级冲突案例",
            "content": "主服务协议优先于标准合同正文会构成高风险冲突，应识别并给出禁止性修改建议。",
            "structured_payload": {
                "must_find_issues": ["standard_contract_priority_conflict"],
                "must_not_claim": ["SCC is fully compliant"],
            },
        },
        {
            "chunk_id": "TC-CN-REVIEW-002",
            "module": "cn_review",
            "title": "权利请求暂缓案例",
            "content": "收到个人权利请求后可视情况暂缓处理属于高风险表述。",
            "structured_payload": {
                "must_find_issues": ["rights_request_weakened"],
                "must_not_claim": ["No issue found"],
            },
        },
        {
            "chunk_id": "TC-CN-REVIEW-003",
            "module": "cn_review",
            "title": "出境责任错配案例",
            "content": "将全部出境合规责任转嫁给受托方应触发责任错配问题。",
            "structured_payload": {
                "must_find_issues": ["compliance_responsibility_shift"],
                "must_not_claim": ["乙方单独承担全部出境手续是合规的"],
            },
        },
    ]
    chunks: list[KnowledgeChunkV2] = []
    for row in rows:
        chunks.append(
            KnowledgeChunkV2(
                chunk_id=row["chunk_id"],
                source_id=row["chunk_id"],
                title=row["title"],
                content=row["content"],
                layer="L3_testcase",
                template_type="none",
                source_kind="testcase",
                module=row["module"],
                jurisdiction="cn",
                doc_type="testcase",
                authority_level="low",
                binding_force="reference",
                allowed_usage=["evaluator", "few_shot"],
                can_be_cited=False,
                can_enter_external_report=False,
                reference_ids=[],
                citation_anchor=row["title"],
                scenario_tags=[row["module"]],
                chunk_strategy="testcase_case",
                path="assessment" if row["module"] == "cn_assessment" else "review",
                structured_payload=dict(row["structured_payload"]),
            )
        )
    return chunks
