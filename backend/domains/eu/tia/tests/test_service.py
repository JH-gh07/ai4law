import json
import re
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from backend.common.citation.registry import CitationRegistry
from backend.domains.eu.tia.agents import create_tia_agents
from backend.domains.eu.tia.schema import TIAChapter, TIARequest
from backend.domains.eu.tia.service import TIAService


class _DisabledLLM:
    enabled = False


class _Reg:
    id = "eu_gdpr_art46"
    title = "GDPR"
    article = "Article 46"
    content = "Appropriate safeguards must be provided for third-country transfers."


class _CitationLLM:
    enabled = True

    def __init__(self) -> None:
        self.calls = 0

    def chat(self, **kwargs) -> str:
        self.calls += 1
        return f"第{self.calls}章应提供适当保障措施 {{{{CIT-EU-GDPR-ART46-P01}}}}。"


class _StaticAgent:
    def __init__(self, result: dict) -> None:
        self.result = result

    def run(self, **kwargs) -> dict:
        return self.result


def _fast_render(task_id, payload, chapters, attachment_notes, citation_registry):
    return {
        "markdown": "outputs/tia/test.md",
        "docx": "outputs/tia/test.docx",
        "zip": "outputs/tia/test.zip",
        "citation_map_json": "outputs/tia/citation_map.json",
    }


def test_tia_generate_report() -> None:
    # This contract test asserts orchestration and output wiring. Live provider
    # verification is recorded separately and must not inherit .env credentials.
    service = TIAService(llm_client=_DisabledLLM())
    service._render = _fast_render
    payload = TIARequest.model_validate(
        {
            "transfer_tool": "scc",
            "data_exporter_profile": "EU Exporter A",
            "data_importer_profile": "US Importer B",
            "third_country_assessment": "存在政府访问风险",
            "supplementary_measures": "端到端加密、严格密钥管理、访问透明报告",
            "final_conclusion": "在补充措施生效前提下SCC可传输",
            "attachments": [
                {
                    "file_role": "transfer_agreement",
                    "file_name": "agreement.pdf",
                    "file_format": "pdf",
                    "storage_uri": "storage://uploads/agreement.pdf",
                }
            ],
        }
    )

    result = service.generate_report(payload)

    assert result.report_path.endswith(".docx")
    assert result.report_path == "outputs/tia/test.docx"
    assert result.output_files["zip"].endswith(".zip")
    assert result.output_files["zip"] == "outputs/tia/test.zip"
    assert result.output_files["citation_map_json"] == "outputs/tia/citation_map.json"
    assert len(result.chapters) == 6
    assert result.transfer_tool == "scc"


def test_us_alias_and_gdpr_roles_enter_structured_context() -> None:
    service = TIAService(llm_client=_DisabledLLM())
    payload = TIARequest.model_validate({
        "transfer_tool": "scc",
        "data_exporter_profile": "EU Exporter",
        "data_importer_profile": "US Importer",
        "third_country_assessment": "FISA 702 and EO 12333 require review.",
        "supplementary_measures": "End-to-end encryption with EU-managed keys.",
        "final_conclusion": "SCC remains conditional on the measures.",
        "attachments": [{
            "file_role": "country_law_analysis",
            "file_name": "country-law.pdf",
            "file_format": "pdf",
            "storage_uri": "storage://uploads/country-law.pdf",
        }],
        "structured_input": {
            "exporter_country": "DE",
            "importer_country": "US",
            "destination_country": "USA",
            "exporter_role": "controller",
            "importer_role": "processor",
        },
    })

    country_risk = service.country_risk.assess(payload.structured_input)
    context = service._build_context(
        payload,
        "HIGH",
        None,
        country_risk,
        {},
        [],
        "",
    )

    assert country_risk.country == "United States"
    assert country_risk.risk_level == "HIGH"
    assert country_risk.gov_access_risk is True
    assert "数据出口方 GDPR 角色：controller" in context
    assert "数据进口方 GDPR 角色：processor" in context


def test_dpo_revision_issues_are_exposed_to_callers(monkeypatch) -> None:
    service = TIAService(llm_client=_DisabledLLM())
    service._render = _fast_render
    service.agents = {
        "rag_planning": _StaticAgent({"queries": []}),
        "attachment_review": _StaticAgent({
            "conflicts": [],
            "missing_evidence": [],
            "overall_evidence_quality": "adequate",
        }),
        "dpo_review": _StaticAgent({
            "review_result": "needs_revision",
            "critical_issues": ["Supplementary measures lack supporting evidence."],
            "non_reliance_warning_needed": False,
            "dpo_position": "Revision required before release.",
            "mandatory_conditions": [],
        }),
    }
    monkeypatch.setattr(
        "backend.domains.eu.tia.service.retrieve_legal_documents",
        lambda *args, **kwargs: type("Hits", (), {"documents": [_Reg()]})(),
    )
    payload = TIARequest.model_validate({
        "transfer_tool": "scc",
        "data_exporter_profile": "EU Exporter A",
        "data_importer_profile": "US Importer B",
        "third_country_assessment": "Government access risk assessed.",
        "supplementary_measures": "Encryption planned.",
        "final_conclusion": "SCC remains conditional on evidence.",
        "attachments": [{
            "file_role": "country_law_analysis",
            "file_name": "country-law.pdf",
            "file_format": "pdf",
            "storage_uri": "storage://uploads/country-law.pdf",
        }],
    })

    result = service.generate_report(payload, task_id="dpo-revision")

    assert "[DPO复核] Supplementary measures lack supporting evidence." in result.consistency_issues


def test_tia_citation_bundle_produces_structured_citations() -> None:
    service = TIAService()
    payload = TIARequest.model_validate(
        {
            "transfer_tool": "scc",
            "data_exporter_profile": "EU Exporter A",
            "data_importer_profile": "US Importer B",
            "third_country_assessment": "US surveillance law may create government access risk.",
            "supplementary_measures": "Encryption, EU key separation, transparency reporting.",
            "final_conclusion": "SCC transfer requires supplementary measures under GDPR Article 46.",
            "attachments": [
                {
                    "file_role": "transfer_agreement",
                    "file_name": "agreement.pdf",
                    "file_format": "pdf",
                    "storage_uri": "storage://uploads/agreement.pdf",
                }
            ],
        }
    )

    class _Reg:
        id = "eu_gdpr_art46"
        title = "GDPR"
        article = "Article 46"
        content = "A controller or processor may transfer personal data to a third country only if appropriate safeguards are provided."

    bundle = service._build_tia_citation_bundle(
        payload=payload,
        regs=[_Reg()],
        level="HIGH",
        route=None,
        country_risk_result=None,
        measure_overall="conditional",
    )

    assert bundle.items
    assert bundle.items[0].citation_id.startswith("CIT-EU-GDPR-ART46-")
    assert bundle.items[0].display_label == "GDPR Article 46"
    assert "{{CIT-EU-GDPR-ART46-" in bundle.prompt_block


def test_tia_real_renderer_generates_pdf_in_bundle() -> None:
    service = TIAService()
    payload = TIARequest.model_validate(
        {
            "transfer_tool": "scc",
            "data_exporter_profile": "EU Exporter A",
            "data_importer_profile": "US Importer B",
            "third_country_assessment": "存在政府访问风险",
            "supplementary_measures": "端到端加密、欧盟境内密钥管理",
            "final_conclusion": "补充措施生效后可传输",
            "attachments": [
                {
                    "file_role": "transfer_agreement",
                    "file_name": "agreement.pdf",
                    "file_format": "pdf",
                    "storage_uri": "storage://uploads/agreement.pdf",
                }
            ],
        }
    )
    chapters = [
        TIAChapter(
            chapter_no=1,
            title="第三国法律评估",
            content="需要补充技术和组织措施。",
            risk_level="HIGH",
        )
    ]

    outputs = service._render(
        "test-pdf-output",
        payload,
        chapters,
        [],
        CitationRegistry(),
    )

    pdf_path = Path(outputs["pdf"])
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(pdf_path).pages) >= 1
    with ZipFile(outputs["zip"]) as bundle:
        assert pdf_path.name in bundle.namelist()


def test_structured_service_parses_real_local_attachment(monkeypatch, tmp_path) -> None:
    """Structured rules and attachment parsing must run in the service path."""
    service = TIAService()
    service.llm_client = _DisabledLLM()
    service.agents = create_tia_agents(None)
    monkeypatch.setattr(
        "backend.domains.eu.tia.service.retrieve_legal_documents",
        lambda *args, **kwargs: type("Hits", (), {"documents": [_Reg()]})(),
    )
    service._render = lambda task_id, payload, chapters, attachment_notes, citation_registry: {
        "markdown": str(tmp_path / "report.md"),
        "docx": str(tmp_path / "report.docx"),
        "pdf": str(tmp_path / "report.pdf"),
        "zip": str(tmp_path / "report.zip"),
        "citation_map_json": str(tmp_path / "citation_map.json"),
    }

    case = json.loads(Path("backend/tests/tia/cases/02_structured_local_attachment.json").read_text())
    payload = TIARequest.model_validate(case["input"])

    result = service.generate_report(payload, task_id="structured-local-attachment")

    assert result.route_decision is not None
    assert result.country_risk is not None
    assert result.country_risk.country == "United States"
    assert result.country_risk.risk_level == "HIGH"
    assert result.country_risk.gov_access_risk is True
    assert result.measure_assessments
    assert any("edpb-recommendations.pdf:" in note for note in result.attachment_notes)
    assert any("fisa-section-702.pdf:" in note for note in result.attachment_notes)
    assert any("cloud-act.pdf:" in note for note in result.attachment_notes)
    assert not any("parse skipped" in note for note in result.attachment_notes)


def test_service_keeps_markdown_map_and_document_ir_citations_in_sync(
    monkeypatch, tmp_path
) -> None:
    """The service must carry one citation identity through every output layer."""
    case = json.loads(Path("backend/tests/tia/cases/02_structured_local_attachment.json").read_text())
    case["input"]["attachments"][0]["storage_uri"] = str(
        Path(case["input"]["attachments"][0]["storage_uri"]).resolve()
    )
    payload = TIARequest.model_validate(case["input"])

    service = TIAService()
    service.llm_client = _CitationLLM()
    service.renderer.schema_first_enabled = True
    service.agents = {
        "rag_planning": _StaticAgent({"queries": [{"query": "GDPR Article 46"}]}),
        "attachment_review": _StaticAgent({
            "conflicts": [],
            "missing_evidence": [],
            "overall_evidence_quality": "adequate",
        }),
        "dpo_review": _StaticAgent({
            "non_reliance_warning_needed": False,
            "dpo_position": "",
            "mandatory_conditions": [],
        }),
    }
    monkeypatch.setattr(
        "backend.domains.eu.tia.service.retrieve_legal_documents",
        lambda *args, **kwargs: type("Hits", (), {"documents": [_Reg()]})(),
    )
    monkeypatch.chdir(tmp_path)

    result = service.generate_report(payload, task_id="citation-sync")

    markdown = Path(result.output_files["markdown"]).read_text(encoding="utf-8")
    citation_map = json.loads(Path(result.output_files["citation_map_json"]).read_text())
    document_ir = json.loads(Path(result.output_files["document_ir_json"]).read_text())

    markdown_numbers = set(re.findall(r"\[(\d+)\]", markdown))
    map_numbers = set(citation_map["footnote_map"])
    claim_refs = {
        citation_id
        for section in document_ir["sections"]
        for block in section["blocks"]
        for citation_id in block.get("citation_refs", [])
    }

    assert markdown_numbers == {"1"}
    assert map_numbers == markdown_numbers
    assert claim_refs == {"CIT-EU-GDPR-ART46-P01"}
