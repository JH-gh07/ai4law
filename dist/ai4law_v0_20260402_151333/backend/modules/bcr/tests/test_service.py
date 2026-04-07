from backend.modules.bcr.schema import BCRRequest
from backend.modules.bcr.service import BCRService


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
    assert result.report_path.endswith("_bcr_review_report.docx")
    assert result.output_files["zip"].endswith("_bcr_output_bundle.zip")
    assert result.rating in {"部分缺失", "高风险", "基本合规"}
    assert len(result.chapters) == 4

