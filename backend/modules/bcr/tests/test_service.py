from backend.modules.bcr.schema import BCRRequest
from backend.modules.bcr.service import BCRService, _build_template_mapping


def test_bcr_generate_report() -> None:
    service = BCRService()
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
    assert result.rating in {"部分缺失", "高风险", "基本合规"}
    assert len(result.chapters) == 4
    detail_chapter = next((chapter for chapter in result.chapters if chapter.title == "详细审查结果"), None)
    assert detail_chapter is not None
    assert detail_chapter.content.startswith("| 检查项 | 主题 | 风险 |")
    assert "| --- | --- | --- | --- | --- | --- |" in detail_chapter.content


def test_bcr_template_mapping_uses_markdown_table_for_detailed_findings() -> None:
    service = BCRService()
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
    chapters = service._generate_chapters(payload, "部分缺失", problems, [], "（暂无）")
    mapping = _build_template_mapping(payload, "部分缺失", problems, chapters, "20260605")

    assert mapping["detailed_findings"].startswith("| 检查项 | 主题 | 风险 |")
    assert "| --- | --- | --- | --- | --- | --- |" in mapping["detailed_findings"]
