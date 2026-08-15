#!/usr/bin/env python3
"""Level C: convert runnable seed requests into frontend developer cases."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "benchmarks/datasets/seed-cases-v1"
INPUTS_DIR = DATASET_DIR / "inputs"
REQUESTS_DIR = DATASET_DIR / "requests-synthetic"
LEDGER_PATH = DATASET_DIR / "levelb-disposition.synthetic.v1.json"
OUTPUT_DIR = DATASET_DIR / "frontend-cases"

MODULE_KEYS = {
    "cn.transfer_diagnosis": "diagnosis",
    "cn.security_assessment": "assessment",
    "cn.pipia": "pipia",
    "cn.document_review": "review",
    "eu.scc_review": "eu_scc",
    "eu.bcr_review": "bcr",
    "eu.dpia": "dpia",
    "eu.tia": "tia",
    "us.eo_14117": "us_14117",
    "us.cpra": "cpra",
}
JURISDICTIONS = {"cn": "CN", "eu": "EU", "us": "US"}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _paths(request: dict[str, Any], record: dict[str, Any], module_key: str) -> list[str]:
    if module_key in {"review", "bcr"}:
        source = record.get("source_docx") or ""
        return [source] if source else []
    if module_key in {"pipia", "cpra", "tia"}:
        paths = [item.get("storage_uri", "") for item in request.get("attachments") or []]
        if paths:
            return [path for path in paths if path]
    if module_key in {"assessment", "dpia", "tia"}:
        source = record.get("source_docx") or ""
        return [source] if source else []
    return list(request.get("uploaded_files") or request.get("attachments") or [])


def _diagnosis(request: dict[str, Any]) -> dict[str, Any]:
    answers = request["answers"]
    count = max(int(answers.get("q3_pii_count", 0)), int(answers.get("q4_spi_count", 0)))
    volume = "1000万条以上" if count >= 10_000_000 else "100-1000万条" if count >= 1_000_000 else "10-100万条" if count >= 100_000 else "10万条以下"
    sensitive = int(answers.get("q4_spi_count", 0)) > 0
    important = answers.get("q2_has_important_data")
    return {
        "company_name": request["company_name"],
        "m1_industry": answers.get("m1_industry", ""),
        "m1_business_channels": [],
        "m1_service_targets": "个人用户或员工",
        "m1_company_size": "中型（51-200人）",
        "m2_core_needs": ["识别业务合规风险点"],
        "m2_core_needs_other": answers.get("q8_purpose", "路径诊断"),
        "m2_had_compliance_issue": "no",
        "m2_deadline": "一般需求（1-3个月）",
        "m3_processes_personal_info": "no" if answers.get("q5_no_personal_info") == "yes" else "yes",
        "m3_personal_info_types": ["健康/基因/生物识别等敏感个人信息" if sensitive else "一般个人信息"],
        "m3_processes_important_data": important if important in {"yes", "no"} else "",
        "m3_important_data_types": [],
        "m3_data_sources": ["业务系统"],
        "m3_processing_activities": ["跨境传输"],
        "m3_data_volume_range": volume,
        "m4_share_to_third_party": "yes" if answers.get("q7_receiver_type") == "third_party" else "no",
        "m4_cross_border_transfer": "yes",
        "m4_cross_border_regions": "见案例原文",
    }


def _assessment(request: dict[str, Any], case_id: str) -> dict[str, Any]:
    return {
        "company_name": request["company_name"], "company_uscc": f"SYNTH{case_id.upper().replace('_', '')}",
        "legal_representative": "模拟负责人", "registered_address": "见案例原文", "company_nature": "企业",
        "industry": request.get("industry", ""), "assessment_start_date": "2026-01-01", "assessment_end_date": "2026-01-31",
        "lead_department": "数据合规部", "participant_departments": "法务部、信息安全部", "third_party_support": False,
        "third_party_name": "", "third_party_scope": "", "scenario_name": "种子案例数据出境安全评估",
        "receiver_name": "见案例原文", "transfer_frequency": "continuous", "is_long_term": True,
        "legal_basis": "个人信息保护法及数据出境安全评估办法", "necessity_basis": "支持原文所述跨境业务目的",
        "receiver_country": request["receiver_country"], "is_ciio": request.get("is_ciio", False),
        "contains_important_data": request.get("contains_important_data", False), "pii_count": request.get("pii_count", 0),
        "spi_count": request.get("spi_count", 0), "transfer_purpose": request["transfer_purpose"],
        "data_inventory_summary": "见种子案例原文及随附材料", "system_chain_summary": "境内业务系统至境外接收方",
        "security_capability_summary": "加密、访问控制和审计日志", "force_override_path": False,
    }


def _pipia(request: dict[str, Any]) -> dict[str, Any]:
    profile, transfer, scope = request["company_profile"], request["transfer_context"], request["personal_info_scope"]
    rights, emergency, evidence = request["rights_protection"], request["emergency_plan"], request.get("path_evidence") or {}
    state = lambda value: "yes" if value is True else "no" if value is False else "unknown"
    return {
        "company_name": profile["company_name"], "company_uscc": profile["company_uscc"], "industry": profile.get("industry", ""),
        "shareholding_structure": "", "actual_controller": "", "overseas_investment": "", "org_structure_privacy_team": "",
        "business_overview": "见案例原文", "processing_activity_overview": transfer["purpose"], "is_ciio": profile.get("is_ciio", False),
        "processing_person_count": profile.get("processing_person_count", 0), "outbound_pi_count": profile.get("outbound_pi_count", 0),
        "outbound_spi_count": profile.get("outbound_spi_count", 0), "route_type": request["route_type"],
        "outbound_scenario_name": "种子案例出境场景", "outbound_frequency": "periodic", "transfer_method": "加密网络传输",
        "domestic_storage": "", "overseas_storage": transfer["recipient_country_region"], "transfer_link": emergency["escalation_path"],
        "purpose": transfer["purpose"], "recipient_name": transfer["recipient_name"], "recipient_country_region": transfer["recipient_country_region"],
        "legal_basis": transfer["legal_basis"], "legality_justification": "见案例原文", "necessity_justification": "见案例原文",
        "pi_categories": ", ".join(scope["pi_categories"]), "spi_categories": ", ".join(scope.get("spi_categories") or []),
        "subject_volume": scope.get("subject_volume", 0), "notice_mechanism": rights["notice_mechanism"],
        "consent_mechanism": rights["consent_mechanism"], "dsar_channel": rights["dsar_channel"],
        "retention_policy": rights["retention_policy"], "incident_response_sla_hours": emergency["incident_response_sla_hours"],
        "escalation_path": emergency["escalation_path"], "attachment_role": request["attachments"][0]["file_role"],
        **{key: state(evidence.get(key)) for key in (
            "recipient_notice_complete", "sensitive_information_classification_confirmed", "consent_evidence_complete",
            "scc_required_clauses_complete", "hr_rules_lawfully_adopted", "employee_handbook_has_explicit_cross_border_terms",
            "collective_agreement_has_explicit_cross_border_terms", "recipient_privacy_policy_provided",
            "certification_body_china_recognized", "certification_legal_obligation_citation_provided",
            "china_data_subject_rights_terms_present")},
        "contract_governing_law": evidence.get("contract_governing_law", ""),
        "contract_exclusive_jurisdiction": evidence.get("contract_exclusive_jurisdiction", ""),
    }


def _review(request: dict[str, Any]) -> dict[str, Any]:
    return {"company_name": "种子案例提交方", "publisher_entity": "种子案例提交方", "document_title": "待审查材料",
            "document_version": "synthetic-v1", "effective_date": "", "applicable_products": "见附件", "applicable_scope": "见附件",
            "is_live_version": False, "document_type": request.get("document_type") or "other", "receiver_name": "待从附件提取",
            "receiver_country": "待从附件提取", "transfer_purpose": "文档专项审查", "processor_identity_disclosed": False,
            "scope_disclosed": False, "collection_purpose_disclosed": False, "processing_method_disclosed": False,
            "category_disclosed": False, "sensitive_pi_disclosed": False, "crossborder_rule_disclosed": False,
            "rights_channel_disclosed": False, "contact_channel": "待审查", "pii_count": 0, "spi_count": 0,
            "has_scc_draft": False, "review_focus": request.get("review_focus") or "识别条款缺口、风险和整改建议"}


def _bcr(request: dict[str, Any]) -> dict[str, Any]:
    company = request["company_name"]
    unknown = "待从上传BCR正文抽取并审查"
    return {"company_name": company, "group_structure": "见上传BCR", "applicant_entity": company,
            "data_flow_scope": "见上传BCR正文", "lead_sa_rationale": unknown, "binding_mechanism": unknown,
            "third_party_beneficiary": unknown, "liability_compensation": unknown, "transparency_notice": unknown,
            "training_audit": unknown, "cooperation_with_sa": unknown, "dp_safeguards": unknown,
            "third_country_assessment": unknown, "government_access_process": unknown, "update_mechanism": unknown,
            "definitions_quality": unknown, "review_focus": "按EDPB BCR要素逐项审查上传正文"}


def _dpia(request: dict[str, Any]) -> dict[str, Any]:
    lines = lambda values: "\n".join(str(item) for item in values or [])
    return {"project_name": request["project_name"], "project_goal": request["project_goal"],
            "need_reason": lines(request.get("dpia_trigger_reasons")), "controller_name": request.get("dpia_owner") or "待确认控制者",
            "dpo_role": request.get("dpo_name") or "DPO", "contact_channel": "privacy@example.test",
            "processing_description": request["processing_flow_description"], "data_types": lines(request.get("data_categories")),
            "includes_special_data": request.get("special_category_data", False), "subject_scale": request.get("data_subject_count", ""),
            "frequency": "持续或按需", "retention_period": request.get("retention_period", ""), "geo_scope": request.get("transfer_destination", ""),
            "has_crossborder_transfer": request.get("cross_border_transfer", False), "data_source": "见案例原文",
            "relationship_context": "见案例原文", "expectation_control": "待评估", "vulnerable_group": "包含弱势主体" if request.get("vulnerable_data_subjects") else "未明确",
            "prior_concerns": "", "novel_technology": "涉及新技术" if request.get("new_technology") else "",
            "lawful_basis": lines(request.get("lawful_basis")), "purpose_and_necessity": request.get("necessity_statement") or "待评估",
            "function_creep_control": "待评估", "minimization_quality": request.get("proportionality_statement") or "待评估",
            "notice_plan": request.get("transparency_information") or "待评估", "rights_support": "待评估",
            "processor_management": "待评估", "risk_assessment": lines(item.get("risk_description", "") for item in request.get("identified_risks") or []),
            "mitigation_measures": lines(request.get("mitigation_measures")), "residual_risk": "待复核",
            "signoff_owner": request.get("dpia_owner") or "项目负责人", "dpo_advice": request.get("dpo_opinion", ""),
            "review_schedule": request.get("review_date", ""), "attachment_role": "other"}


def _tia(request: dict[str, Any]) -> dict[str, Any]:
    structured = request.get("structured_input") or {}
    return {"structured_input_override": structured, "data_exporter_name": "Seed Exporter",
            "data_importer_name": "Seed Importer", "importer_country_region": structured.get("importer_country", "Unknown"),
            "transfer_purpose": structured.get("transfer_purpose", "种子案例跨境处理"),
            "data_categories": ", ".join(structured.get("data_categories") or []),
            "sensitive_data_description": ", ".join(structured.get("special_category_types") or []),
            "data_subject_categories": ", ".join(structured.get("data_subjects") or []), "transfer_frequency": "continuous",
            "transfer_tool": request["transfer_tool"], "law_assessed": False, "law_findings": "待评估",
            "pre_effectiveness": "待评估", "supplementary_technical": "见案例原文", "supplementary_contractual": "待评估",
            "supplementary_organizational": "待评估", "post_effectiveness": "待评估", "key_actions": "完成人工复核",
            "dpo_opinion": "未签署", "review_date": "", "attachment_role": "other"}


def _eu_scc(request: dict[str, Any]) -> dict[str, Any]:
    text, module = request["scc_text"], request["declared_module_type"]
    role = {"Module One": "c2c", "Module Two": "c2p", "Module Three": "p2p", "Module Four": "p2c"}[module]
    find = lambda label, default: (re.search(label + r"\s*([^\n.]+)", text).group(1).strip() if re.search(label + r"\s*([^\n.]+)", text) else default)
    return {"project_name_override": request["project_name"], "scc_text_override": text,
            "exporter_name": find("Data exporter:", request.get("company_name", "Seed Exporter")),
            "importer_name": find("Data importer:", "Seed Importer"), "importer_country": "见SCC附件",
            "transfer_role": role, "declared_module_type": module, "scc_version": "eu_2021",
            "transfer_purpose": find("Purpose and processing:", "跨境数据处理"), "data_categories": "见Annex I",
            "data_subject_categories": "见Annex I", "transfer_frequency": "continuous", "retention_rule": "不超过处理必要期限",
            "tom_summary": "加密、访问控制、审计日志和事件响应", "onward_transfer_control": "须经授权并施加同等保障",
            "rights_and_complaint": "提供数据主体权利与投诉渠道", "government_access_response": "记录并依法挑战政府访问请求",
            "supplementary_clause_review": "未签署测试文本，仅用于审查链路", "has_tia": request.get("has_tia", False),
            "has_supplementary_measures": request.get("has_supplementary_measures", False), "pii_count": 0, "spi_count": 0,
            "has_scc_draft": True}


def _us14117(request: dict[str, Any]) -> dict[str, Any]:
    item, entity = request["data_items"][0], request["recipient_entities"][0]
    return {"data_items_override": request["data_items"], "recipient_entities_override": request["recipient_entities"],
            "access_persons_override": request.get("access_persons") or [], "security_measures_override": request.get("security_measures") or [],
            "company_name": request["company_name"], "project_name": request["project_name"],
            "transaction_description": request["transaction_description"], "transaction_type": request["transaction_type"],
            "data_item_name": item["data_item_name"], "data_description": item.get("data_description", ""),
            "doj_data_category": item.get("doj_data_category", ""), "us_person_count": item.get("us_person_count", 0),
            "entity_name": entity["entity_name"], "country_of_registration": entity["country_of_registration"],
            "government_control": entity.get("government_control", False), "entity_role": entity.get("entity_role", "other"),
            "onward_transfer": request.get("onward_transfer", False), "onward_transfer_description": request.get("onward_transfer_description", ""),
            "security_measures_summary": "；".join(item.get("description") or item["measure_name"] for item in request.get("security_measures") or []),
            "review_focus": "核查EO 14117数据类别、阈值、接收实体和交易类型"}


def _cpra(request: dict[str, Any]) -> dict[str, Any]:
    return {"company_name": request["company_name"], "dba_name": "", "cpra_applicability_selfcheck": "授权模拟案例，适用性待系统判断",
            "business_model": request["business_model"], "data_lifecycle": request["data_lifecycle"], "data_categories": "见数据生命周期",
            "notice_and_consent": request["notice_and_consent"], "privacy_policy_url": "",
            "consumer_rights_process": request["consumer_rights_process"], "identity_verification_method": "见权利流程",
            "rights_sla": "45日或依法延长", "opt_out_and_sale_sharing": request["opt_out_and_sale_sharing"],
            "spi_usage_summary": "见案例原文", "vendor_management": request.get("vendor_management", ""),
            "ui_dark_pattern_check": "待审查", "review_focus": "核查通知、权利、退出和供应商治理"}


MAPPERS = {"diagnosis": _diagnosis, "pipia": _pipia, "review": _review, "bcr": _bcr,
           "dpia": _dpia, "tia": _tia, "eu_scc": _eu_scc, "us_14117": _us14117, "cpra": _cpra}


def build_cases() -> list[dict[str, Any]]:
    ledger = _read_json(LEDGER_PATH)
    records = {path.stem.removesuffix(".input"): _read_json(path) for path in INPUTS_DIR.glob("*.input.json")}
    cases = []
    for disposition in ledger["dispositions"]:
        if disposition["levelb"] != "converted":
            continue
        case_id, module_id = disposition["case_id"], disposition["module_id"]
        record, request = records[case_id], _read_json(REQUESTS_DIR / f"{case_id}.request.json")
        module_key = MODULE_KEYS[module_id]
        defaults = _assessment(request, case_id) if module_key == "assessment" else MAPPERS[module_key](request)
        synthetic = disposition.get("source_faithfulness") == "synthetic_only"
        cases.append({"caseId": case_id, "moduleKey": module_key,
                      "name": f"{case_id} · {'模拟' if synthetic else '源数据'} · 未签署",
                      "description": f"{record['declared_task_name']}；无expected.json，仅验证回填、请求构建与Schema。",
                      "jurisdiction": JURISDICTIONS[record["jurisdiction"]], "formDefaults": defaults,
                      "backendFilePaths": _paths(request, record, module_key),
                      "sourceKind": "synthetic_fixture" if synthetic else "source_faithful",
                      "goldStatus": "unsigned", "sourceRequestPath": disposition["request_path"]})
    return sorted(cases, key=lambda item: item["caseId"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    cases = build_cases()
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["moduleKey"]] = counts.get(case["moduleKey"], 0) + 1
    print(f"frontend cases: {len(cases)} {counts}")
    if not args.write:
        return 0
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for case in cases:
        (OUTPUT_DIR / f"{case['caseId']}.case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = {"schema_version": "1.0", "gold_status": "unsigned", "cases": cases}
    (OUTPUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
