"""task073 T01 — 旧 JSON（不含控制字段）反序列化兼容测试。

证明 ``control_decision`` / ``clarification_questions`` 为 additive 字段，
旧 fixture 字节/字段兼容，旧 consumer 仍可解析。
"""
from __future__ import annotations

from backend.domains.cn.security_assessment.schema import AssessmentResult
from backend.domains.cn.transfer_diagnosis.schema import DiagnosisResult


def test_diagnosis_result_old_json_parses_without_control_fields():
    old = {
        "recommended_path": "security_assessment",
        "legal_basis": ["个保法第38条"],
        "rationale": "触发安全评估",
        "action_items": ["整理清单"],
        "risk_level": "HIGH",
        "conclusion_source": "rule",
        "confidence": "HIGH",
        "matched_rule_id": "rule-1",
        "final_explanation": "",
        "uncertainty_notes": [],
        "fact_provenance": {},
        "missing_facts": [],
        "requires_human_review": False,
    }
    result = DiagnosisResult.model_validate(old)
    assert result.control_decision is None
    assert result.clarification_questions == []


def test_assessment_result_old_json_parses_without_control_fields():
    old = {
        "task_id": "task-1",
        "state": "COMPLETED",
        "report_path": "outputs/report.md",
        "output_files": {},
        "profile": {
            "company_name": "测试科技有限公司",
            "industry": "金融",
            "is_ciio": False,
            "contains_important_data": False,
            "pii_count": 0,
            "spi_count": 0,
            "transfer_purpose": "跨境业务合作",
            "receiver_country": "新加坡",
        },
        "regulations": [],
        "chapters": [],
        "consistency_issues": [],
    }
    result = AssessmentResult.model_validate(old)
    assert result.control_decision is None
    assert result.clarification_questions == []
    assert result.state.value == "COMPLETED"
