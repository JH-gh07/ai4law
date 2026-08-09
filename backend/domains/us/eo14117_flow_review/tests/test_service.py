import json
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from backend.domains.us.eo14117_flow_review.schema import CNFlowRequest
from backend.domains.us.eo14117_flow_review.service import CNFlowService


class _DisabledLLM:
    enabled = False


def test_cn_flow_generate_report(tmp_path, monkeypatch) -> None:
    service = CNFlowService(llm_client=_DisabledLLM())
    payload = CNFlowRequest.model_validate(
        {
            "company_name": "测试企业",
            "transfer_purpose": "全球客服与风控",
            "data_categories": ["账户信息", "设备信息"],
            "sensitive_data_flags": ["生物识别"],
            "us_person_count": 100000,
            "transaction_type": "vendor_agreement",
            "doj_data_category_by_item": {
                "账户信息": "covered_personal_identifiers",
                "设备信息": "not_14117_data",
                "生物识别": "biometric_identifiers",
            },
            "recipient_entities": [
                {
                    "entity_name": "US ServiceCo",
                    "country_region": "United States",
                    "entity_role": "processor",
                    "is_restricted_party": False,
                }
            ],
            "transfer_chain": "CN -> US processor -> subprocessor",
            "attachments": [
                {
                    "file_role": "data_inventory",
                    "file_name": "data.csv",
                    "file_format": "csv",
                    "storage_uri": "storage://uploads/data.csv",
                },
                {
                    "file_role": "entity_inventory",
                    "file_name": "entity.csv",
                    "file_format": "csv",
                    "storage_uri": "storage://uploads/entity.csv",
                },
            ],
        }
    )

    result = service.generate_report(payload)
    assert result.report_path.endswith(".docx")
    assert "_14117_风险评估结论报告_草案_" in result.report_path
    assert result.output_files["pdf"].endswith(".pdf")
    assert result.output_files["xlsx"].endswith(".xlsx")
    assert result.output_files["zip"].endswith(".zip")
    assert result.output_files["facts_json"].endswith(".json")
    assert result.output_files["issue_list_json"].endswith(".json")
    assert result.output_files["evidence_chain_json"].endswith(".json")
    assert result.output_files["trace_manifest"].endswith(".json")
    pdf_path = Path(result.output_files["pdf"])
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(pdf_path).pages) >= 1
    with ZipFile(result.output_files["zip"]) as bundle:
        assert pdf_path.name in bundle.namelist()
    assert result.risk_items

    manifest = json.loads(Path(result.output_files["trace_manifest"]).read_text(encoding="utf-8"))
    event_names = [item["name"] for item in manifest["events"]]
    assert "cn_flow_request" in event_names
    assert "facts_built" in event_names
    assert "issues_built" in event_names
    assert "evidence_built" in event_names
    assert "context_pack_built" in event_names
