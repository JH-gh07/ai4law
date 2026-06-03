"""CN SCC service tests — unit tests use fallback mode (no LLM network calls)."""
import zipfile
from pathlib import Path

import pytest
from docx import Document

from backend.modules.scc.schema import SCCRequest
from backend.modules.scc.service import SCCService


# ── Helper: create service with or without LLM ──

def _make_service(use_llm: bool = False) -> SCCService:
    """Create SCC service instance.

    use_llm=False: fast fallback mode (no network) for unit tests.
    use_llm=True: real LLM client from settings (requires valid API key).
    """
    if not use_llm:
        return SCCService(llm_client=None)
    return SCCService()


def test_scc_generate_report_fallback() -> None:
    """Full pipeline test in fallback mode — validates agent orchestration."""
    service = _make_service(use_llm=False)
    payload = SCCRequest(
        company_name="测试公司",
        receiver_name="Test SG",
        receiver_country="Singapore",
        transfer_purpose="跨境客服",
        pii_count=120000,
        spi_count=500,
        has_scc_draft=False,
        uploaded_files=[],
    )

    result = service.generate_report(payload)

    # Core output assertions
    assert result.report_path.endswith(".docx")
    assert "_SCC_" in result.report_path
    assert "markdown" in result.output_files
    assert result.output_files["markdown"].endswith(".md")
    assert "_SCC_" in result.output_files["markdown"]
    assert len(result.chapters) == 4
    assert any("No SCC draft provided" in issue for issue in result.consistency_issues)

    # New agent pipeline assertions
    assert result.path_diagnosis is not None, "Path diagnosis agent must run"
    assert result.path_diagnosis.recommended_path in (
        "standard_contract", "security_assessment", "certification", "exemption", "uncertain"
    )
    assert result.facts is not None and len(result.facts) > 0, "Fact builder must produce facts"
    assert result.issues is not None and len(result.issues) > 0, "Issue builder must produce issues"
    assert result.evidence_chain is not None, "Evidence builder must produce evidence chain"
    assert result.rag_query_plans is not None, "RAG planning agent must run"
    assert result.report_review is not None, "Report review agent must run"
    assert result.clarification is not None, "Clarification agent must run"
    assert result.explanation is not None, "Explanation agent must run"
    assert result.trace_manifest_path, "Trace manifest must be generated"


def test_scc_generate_with_data_fields() -> None:
    """Test pipeline with data field classification."""
    service = _make_service(use_llm=False)
    payload = SCCRequest(
        company_name="AI招聘公司",
        receiver_name="US Parent Corp",
        receiver_country="United States",
        transfer_purpose="员工数据跨境分析",
        pii_count=5000,
        spi_count=50,
        has_scc_draft=True,
        data_fields=[
            {"field_name": "Hashed_Device_ID", "field_description": "SHA256 hashed device",
             "user_pii_label": "not_personal_information", "processing_method": "hashed",
             "business_purpose": "用户行为分析"},
        ],
        contract_summary="标准合同草案包含数据保护附件但缺少法律政策变化应对条款",
    )

    result = service.generate_report(payload)

    assert result.path_diagnosis is not None
    assert len(result.field_classifications) > 0, "Must classify data fields"
    assert len(result.contract_findings) > 0, "Must review contract"
    assert len(result.legal_basis_reviews) > 0, "Must review legal basis"
    assert len(result.evidence_verifications) > 0, "Must verify evidence"

    # Check field classification result
    for fc in result.field_classifications:
        assert fc.field_name
        assert fc.agent_judgment in (
            "personal_information", "not_personal_information",
            "sensitive_personal_information", "potential_personal_information",
            "potential_sensitive_personal_information",
        )
        assert fc.risk in ("LOW", "MEDIUM", "HIGH", "BLOCKER")


def test_scc_generate_security_assessment_trigger() -> None:
    """Test that large PII volumes correctly trigger security assessment path."""
    service = _make_service(use_llm=False)
    payload = SCCRequest(
        company_name="大型社交平台",
        receiver_name="US Data Center",
        receiver_country="United States",
        transfer_purpose="用户数据分析与广告推荐",
        pii_count=5_000_000,  # Over 1M threshold
        spi_count=50_000,      # Over 10K threshold
        has_scc_draft=False,
    )

    result = service.generate_report(payload)
    assert result.path_diagnosis is not None
    assert result.path_diagnosis.recommended_path == "security_assessment", \
        f"Expected security_assessment, got {result.path_diagnosis.recommended_path}"
    assert result.path_diagnosis.confidence > 0.8

    # Check that BLOCKER severity issues are generated
    blocker_issues = [i for i in result.issues if i.get("severity") == "BLOCKER"]
    assert len(blocker_issues) > 0, "Must have BLOCKER issues for security assessment path"


def test_scc_generate_hr_exemption() -> None:
    """Test HR management exemption scenario."""
    service = _make_service(use_llm=False)
    payload = SCCRequest(
        company_name="跨国制造企业",
        receiver_name="Japan Subsidiary",
        receiver_country="Japan",
        transfer_purpose="员工数据出境用于人力资源管理",
        pii_count=500,
        spi_count=0,
        has_scc_draft=True,
        is_hr_management=True,
        has_exemption_material=False,
        legal_basis=["hr_management"],
        employee_handbook_summary="员工手册提及数据保护但未专门规定数据出境",
    )

    result = service.generate_report(payload)
    assert result.path_diagnosis is not None
    # With no exemption evidence, should recommend standard contract
    assert result.path_diagnosis.recommended_path in ("standard_contract", "exemption")
    # Should have blocking issues about evidence
    assert len(result.path_diagnosis.blocking_issues) > 0


def test_scc_explanation_output() -> None:
    """Test that explanation agent produces readable output."""
    service = _make_service(use_llm=False)
    payload = SCCRequest(
        company_name="测试企业", receiver_name="EU Partner", receiver_country="Germany",
        transfer_purpose="客户支持", pii_count=1000, spi_count=0, has_scc_draft=True,
    )

    result = service.generate_report(payload)
    assert result.explanation is not None
    assert len(result.explanation.segments) >= 4, \
        f"Explanation should have at least 4 segments, got {len(result.explanation.segments)}"
    assert result.explanation.summary, "Explanation must have summary"

    # Check segment structure
    for seg in result.explanation.segments:
        assert seg.step_label
        assert seg.description


@pytest.mark.slow
def test_scc_generate_annotated_docx(tmp_path: Path) -> None:
    """Integration test: annotated DOCX generation (requires LLM, may be slow)."""
    source_docx = tmp_path / "sample.docx"
    document = Document()
    document.add_paragraph("个人信息出境标准合同")
    document.add_paragraph("甲方名称：测试公司")
    document.add_paragraph("乙方名称：Example Recipient Inc.")
    document.add_paragraph("双方应根据适用法律持续评估跨境传输风险。")
    document.save(source_docx)

    service = _make_service(use_llm=False)
    payload = SCCRequest(
        company_name="测试公司",
        receiver_name="Example Recipient Inc.",
        receiver_country="Singapore",
        transfer_purpose="客户支持与系统运维",
        pii_count=200,
        spi_count=10,
        has_scc_draft=True,
        uploaded_files=[str(source_docx)],
    )

    result = service.generate_report(payload)

    assert "annotated_docx" in result.output_files
    annotated_path = Path(result.output_files["annotated_docx"])
    assert annotated_path.exists()

    with zipfile.ZipFile(annotated_path, "r") as archive:
        assert "word/comments.xml" in archive.namelist()
        document_xml = archive.read("word/document.xml").decode("utf-8")
        comments_xml = archive.read("word/comments.xml").decode("utf-8")

    assert "commentRangeStart" in document_xml
    assert "commentReference" in document_xml
    assert "风险点名称" in comments_xml
