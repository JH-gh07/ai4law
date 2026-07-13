from backend.common.workflow import EvidenceItem, FactItem, GenerationContextPack, IssueItem
from backend.modules.assessment.chapter_generator import (
    ASSESSMENT_CHAPTER_KEYS,
    AssessmentChapterGenerator,
    build_context_block_from_pack,
)
from backend.modules.assessment.schema import CompanyProfile, RegulationHit


def _context_pack(issues: list[IssueItem], evidence_chain: list[EvidenceItem] | None = None) -> GenerationContextPack:
    return GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[
            FactItem(
                fact_id="FACT-request-company_name",
                source_type="schema",
                field_path="request.company_name",
                value="测试公司",
                normalized_value="测试公司",
            ),
            FactItem(
                fact_id="FACT-diagnosis_result-recommended_path",
                source_type="diagnosis",
                field_path="diagnosis_result.recommended_path",
                value="security_assessment",
                normalized_value="security_assessment",
            ),
        ],
        diagnosis_result={"recommended_path": "security_assessment"},
        regulations=[
            {
                "source_id": "reg-pipl-40",
                "title": "个人信息保护法",
                "article": "第40条",
                "snippet": "CIIO 个人信息出境相关要求。",
            }
        ],
        issues=issues,
        evidence_chain=evidence_chain or [],
        attachment_notes=[],
        risk_summary={"risk_level": "HIGH"},
    )


def test_assessment_chapter_titles_have_stable_keys() -> None:
    assert ASSESSMENT_CHAPTER_KEYS["出境活动概述"] == "overview"
    assert ASSESSMENT_CHAPTER_KEYS["数据类型与规模"] == "data_scope"
    assert ASSESSMENT_CHAPTER_KEYS["剩余风险与整改建议"] == "risk_remediation"
    assert ASSESSMENT_CHAPTER_KEYS["综合评估结论"] == "conclusion"


def test_context_block_contains_issues_diagnosis_and_material_gap() -> None:
    issue = IssueItem(
        issue_id="ISSUE-missing-attachments",
        title="申报支撑材料缺失",
        description="当前请求未提供上传附件。",
        category="documentation",
        severity="MEDIUM",
        fact_refs=["FACT-request-uploaded_files"],
        recommended_action="需补充数据清单、隐私政策和合同材料。",
        affects_outputs=["risk_remediation"],
    )

    prompt = build_context_block_from_pack(_context_pack([issue]), "risk_remediation")

    assert "ISSUE-missing-attachments" in prompt
    assert "recommended_path" in prompt
    assert "security_assessment" in prompt
    assert "需补充" in prompt or "材料缺失" in prompt


def test_context_block_contains_attachment_notes_when_present() -> None:
    pack = _context_pack([])
    pack.attachment_notes = [
        {
            "source_ref": "privacy_policy.pdf",
            "summary": "隐私政策未明确境外接收方名称和联系方式。",
        }
    ]

    prompt = build_context_block_from_pack(pack, "risk_remediation")

    assert "privacy_policy.pdf" in prompt
    assert "隐私政策未明确境外接收方名称和联系方式" in prompt


def test_context_block_loses_issue_id_when_issue_list_is_removed() -> None:
    prompt = build_context_block_from_pack(_context_pack([]), "risk_remediation")

    assert "ISSUE-" not in prompt


def test_context_block_contains_evidence_chain() -> None:
    issue = IssueItem(
        issue_id="ISSUE-ciio-security-assessment",
        title="CIIO 触发安全评估路径",
        description="输入事实显示企业属于 CIIO。",
        category="path",
        severity="HIGH",
        fact_refs=["FACT-request-is_ciio"],
        rule_refs=["diagnosis:ciio", "reg-pipl-40"],
        evidence_refs=["EVIDENCE-ciio-security-assessment"],
        recommended_action="按安全评估申报要求准备材料。",
        affects_outputs=["overview"],
    )
    evidence = EvidenceItem(
        evidence_id="EVIDENCE-ciio-security-assessment",
        claim="CIIO 事实触发安全评估路径判断",
        fact_refs=["FACT-request-is_ciio"],
        rule_refs=["diagnosis:ciio", "reg-pipl-40"],
        conclusion="应按安全评估路径准备申报和自评估材料。",
        confidence=0.9,
        used_by=["ISSUE-ciio-security-assessment", "overview"],
    )

    prompt = build_context_block_from_pack(_context_pack([issue], [evidence]), "overview")

    assert "EVIDENCE-ciio-security-assessment" in prompt
    assert "CIIO 事实触发安全评估路径判断" in prompt


def test_final_llm_prompt_contains_context_pack_issue() -> None:
    issue = IssueItem(
        issue_id="ISSUE-missing-attachments",
        title="申报支撑材料缺失",
        description="当前请求未提供上传附件。",
        category="documentation",
        severity="MEDIUM",
        fact_refs=["FACT-request-uploaded_files"],
        recommended_action="需补充数据清单、隐私政策和合同材料。",
        affects_outputs=["risk_remediation"],
        evidence_refs=["EVIDENCE-missing-attachments"],
    )
    evidence = EvidenceItem(
        evidence_id="EVIDENCE-missing-attachments",
        claim="附件缺失影响材料完整性风险判断",
        fact_refs=["FACT-request-uploaded_files"],
        rule_refs=[],
        conclusion="未上传申报支撑材料会削弱报告的材料审查和证据追溯能力。",
        confidence=0.75,
        used_by=["ISSUE-missing-attachments", "risk_remediation"],
    )
    captured_prompts: list[str] = []

    class FakeLLM:
        enabled = True

        def chat_with_metadata(self, system: str, user: str, temperature: float, max_tokens: int) -> dict:
            captured_prompts.append(user)
            return {
                "content": "测试段落【依据：个人信息保护法第40条】",
                "fallback": False,
            }

    generator = AssessmentChapterGenerator(llm_client=FakeLLM())
    profile = CompanyProfile(
        company_name="测试公司",
        industry="互联网医疗",
        is_ciio=True,
        contains_important_data=False,
        pii_count=1,
        spi_count=0,
        transfer_purpose="模型训练",
        receiver_country="新加坡",
    )
    hits = [
        RegulationHit(
            source_id="reg-pipl-40",
            title="个人信息保护法",
            article="第40条",
            snippet="CIIO 个人信息出境相关要求。",
        )
    ]

    generator.generate(profile, hits, context_pack=_context_pack([issue], [evidence]))

    assert any("ISSUE-missing-attachments" in prompt for prompt in captured_prompts)
    assert any("recommended_path" in prompt for prompt in captured_prompts)
    assert any("security_assessment" in prompt for prompt in captured_prompts)
    assert any("EVIDENCE-missing-attachments" in prompt for prompt in captured_prompts)
