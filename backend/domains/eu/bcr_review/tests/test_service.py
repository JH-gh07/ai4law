from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from backend.common.citation.registry import registry_from_documents
from backend.common.rag.retriever import RegulationDoc
from backend.domains.eu.bcr_review.schema import BCRFinding, BCRRequest
from backend.domains.eu.bcr_review.service import BCRService, _build_template_mapping


class _DisabledLLM:
    enabled = False


class _CitationLLM:
    enabled = True

    def chat(self, **kwargs) -> str:
        marker_line = next(
            line for line in kwargs["user"].splitlines() if line.startswith("{{CIT-")
        )
        marker = marker_line.split(" = ", 1)[0]
        return f"集团规则应当具备法律约束力。{marker}"


def test_bcr_generate_report() -> None:
    service = BCRService(llm_client=_DisabledLLM())
    payload = BCRRequest.model_validate(
        {
            "company_name": "示例集团",
            "review_items": [
                {
                    "code": "3.2-C1",
                    "title": "结构完整性",
                    "score": "partial",
                    "finding": "章节覆盖不完整",
                    "legal_basis": "GDPR 第47条",
                    "recommendation": "补齐约束力与权利章节",
                    "evidence": "BCR-v1 第3章",
                },
                {
                    "code": "3.2-C2",
                    "title": "集团内部约束力",
                    "score": "compliant",
                    "finding": "已覆盖",
                    "legal_basis": "GDPR 第47条",
                    "recommendation": "保持",
                    "evidence": "BCR-v1 第4章",
                },
            ],
            "attachments": [],
        }
    )

    result = service.generate_report(payload)
    assert result.report_path.endswith(".docx")
    assert "_BCR-C_合规审查报告_草案_" in result.report_path
    assert result.output_files["zip"].endswith(".zip")
    assert "_BCR-C_输出包_草案_" in result.output_files["zip"]
    pdf_path = Path(result.output_files["pdf"])
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(pdf_path).pages) >= 1
    with ZipFile(result.output_files["zip"]) as bundle:
        assert pdf_path.name in bundle.namelist()
    assert result.rating in {"部分缺失", "高风险", "基本合规"}
    assert len(result.chapters) == 4
    detail_chapter = next((chapter for chapter in result.chapters if chapter.title == "详细审查结果"), None)
    assert detail_chapter is not None
    assert detail_chapter.content.startswith("| 检查项 | 主题 | 风险 |")
    assert "| --- | --- | --- | --- | --- | --- |" in detail_chapter.content


def test_bcr_template_mapping_uses_markdown_table_for_detailed_findings() -> None:
    service = BCRService(llm_client=_DisabledLLM())
    payload = BCRRequest.model_validate(
        {
            "company_name": "示例集团",
            "review_items": [
                {
                    "code": "3.2-C1",
                    "title": "Binding nature and scope",
                    "score": "partial",
                    "finding": "条款已涉及但表述不充分",
                    "legal_basis": "GDPR Art.47",
                    "recommendation": "补齐内部约束力。",
                    "evidence": "第3章",
                },
            ],
            "attachments": [],
        }
    )

    problems = service._extract_problems(payload)
    chapters = service._generate_chapters(
        payload, "部分缺失", problems, registry_from_documents([], jurisdiction="EU"), "（暂无）"
    )
    mapping = _build_template_mapping(payload, "部分缺失", problems, chapters, "20260605")

    assert mapping["detailed_findings"].startswith("| 检查项 | 主题 | 风险 |")
    assert "| --- | --- | --- | --- | --- | --- |" in mapping["detailed_findings"]


def test_bcr_document_driven_renderer_generates_pdf_in_bundle() -> None:
    service = BCRService(llm_client=_DisabledLLM())
    payload = BCRRequest.model_validate(
        {"company_name": "文档审查集团", "review_items": [], "attachments": []}
    )
    finding = BCRFinding(
        finding_id="BCR-TEST-01",
        requirement_id="BCR-C-1.1",
        title="约束力不足",
        risk_level="HIGH",
        finding="集团内部约束机制不完整。",
        legal_basis=["GDPR Article 47"],
        recommendation="补充集团内部约束条款。",
    )
    sections = [(f"章节 {index}", ["审查内容"]) for index in range(8)]
    registry = registry_from_documents(
        [
            RegulationDoc(
                id="gdpr",
                title="General Data Protection Regulation",
                article="47",
                content="Binding corporate rules shall be legally binding.",
                jurisdiction="eu",
            )
        ],
        jurisdiction="EU",
    )
    registry.assign_footnote_number(next(iter(registry)).citation_id)

    outputs = service._render_document_driven(
        "document-pdf-output",
        payload,
        "高风险",
        [finding],
        [],
        sections,
        {"bcr_type": "BCR-C"},
        registry,
    )

    pdf_path = Path(outputs["pdf"])
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(pdf_path).pages) >= 1
    with ZipFile(outputs["zip"]) as bundle:
        assert pdf_path.name in bundle.namelist()
        assert "citation_map.json" in bundle.namelist()
    assert Path(outputs["citation_map_json"]).exists()


def test_bcr_chapter_generation_uses_shared_citation_registry() -> None:
    service = BCRService(llm_client=_CitationLLM())
    payload = BCRRequest.model_validate(
        {"company_name": "引用测试集团", "review_items": [], "attachments": []}
    )
    registry = registry_from_documents(
        [
            RegulationDoc(
                id="gdpr",
                title="General Data Protection Regulation",
                article="47",
                content="Binding corporate rules shall be legally binding.",
                jurisdiction="eu",
            )
        ],
        jurisdiction="EU",
    )

    chapters = service._generate_chapters(
        payload,
        "基本合规",
        [],
        registry,
        "General Data Protection Regulation 第47条",
    )

    generated = next(chapter for chapter in chapters if chapter.title == "报告摘要")
    assert generated.content.endswith("[1]")
    assert generated.citations == ["CIT-EU-GDPR-ART47-P01"]


def test_bcr_render_writes_shared_citation_map(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    service = BCRService(llm_client=_DisabledLLM())
    service.schema_first_enabled = False
    payload = BCRRequest.model_validate(
        {"company_name": "引用测试集团", "review_items": [], "attachments": []}
    )
    registry = registry_from_documents(
        [
            RegulationDoc(
                id="gdpr",
                title="General Data Protection Regulation",
                article="47",
                content="Binding corporate rules shall be legally binding.",
                jurisdiction="eu",
            )
        ],
        jurisdiction="EU",
    )
    citation_id = next(iter(registry)).citation_id
    registry.assign_footnote_number(citation_id)

    outputs = service._render(
        "citation-map-task",
        payload,
        "基本合规",
        [],
        [],
        [],
        registry,
    )

    citation_map = Path(outputs["citation_map_json"])
    assert citation_map.name == "citation_map.json"
    assert '"CIT-EU-GDPR-ART47-P01"' in citation_map.read_text(encoding="utf-8")


def test_bcr_schema_first_service_exposes_document_ir(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    service = BCRService(llm_client=_DisabledLLM())
    service.schema_first_enabled = True
    payload = BCRRequest.model_validate(
        {
            "company_name": "Schema-first BCR 集团",
            "review_items": [
                {
                    "code": "3.2-C1",
                    "title": "结构完整性",
                    "score": "partial",
                    "finding": "章节覆盖不完整",
                    "legal_basis": "GDPR 第47条",
                    "recommendation": "补齐约束力章节",
                    "evidence": "BCR-v1 第3章",
                }
            ],
            "attachments": [],
        }
    )

    result = service.generate_report(payload, task_id="schema-first-service")

    assert "document_ir_json" in result.output_files
    assert Path(result.output_files["document_ir_json"]).exists()


def test_bcr_document_upload_path_exposes_document_ir(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "bcr.txt"
    source.write_text(
        "Binding corporate rules are legally binding for all group entities.\n"
        "Complaints and onward transfers are covered by internal procedures.",
        encoding="utf-8",
    )
    service = BCRService(llm_client=_DisabledLLM())
    service.schema_first_enabled = True
    payload = BCRRequest.model_validate(
        {
            "company_name": "文档驱动 BCR 集团",
            "review_items": [],
            "attachments": [],
            "uploaded_documents": [
                {
                    "file_id": "bcr-upload-1",
                    "file_name": "bcr.txt",
                    "file_type": "txt",
                    "file_path": str(source),
                    "document_role": "main_bcr_document",
                }
            ],
        }
    )

    result = service.generate_report(payload, task_id="document-driven-schema-first")

    assert "document_ir_json" in result.output_files
    assert Path(result.output_files["document_ir_json"]).exists()
