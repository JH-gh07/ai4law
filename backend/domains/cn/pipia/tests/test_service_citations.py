from __future__ import annotations

import json
import re
from pathlib import Path

from backend.common.rag.retriever import RegulationDoc
from backend.domains.cn.pipia.schema import PIPIARequest
from backend.domains.cn.pipia.service import PIPIAService


class _FirstCitationLLM:
    enabled = True

    def __init__(self) -> None:
        self.calls = 0

    def chat(self, **kwargs) -> str:
        self.calls += 1
        marker_line = next(
            line for line in kwargs["user"].splitlines() if line.startswith("{{CIT-")
        )
        marker = marker_line.split(" = ", 1)[0]
        return f"第{self.calls}章：向境外提供个人信息前应履行告知义务并取得单独同意。{marker}"


def _payload(attachment_path: Path) -> PIPIARequest:
    return PIPIARequest.model_validate(
        {
            "route_type": "scc_filing",
            "company_profile": {
                "company_name": "海淘优选（杭州）科技有限公司",
                "company_uscc": "91330100PIPIATEST01",
                "is_ciio": False,
                "processing_person_count": 8_000_000,
                "outbound_pi_count": 500_000,
                "outbound_spi_count": 50_000,
                "industry": "跨境电子商务",
            },
            "transfer_context": {
                "purpose": "个性化营销与市场分析",
                "recipient_name": "SeaCommerce Pte. Ltd.",
                "recipient_country_region": "新加坡",
                "legal_basis": "单独同意",
            },
            "personal_info_scope": {
                "pi_categories": ["偏好标签", "浏览记录", "订单摘要"],
                "spi_categories": ["可能推断健康或孕产状态的偏好标签"],
                "subject_volume": 500_000,
            },
            "rights_protection": {
                "notice_mechanism": "隐私政策仅概括披露关联方",
                "consent_mechanism": "单独同意截图，缺少批量记录",
                "dsar_channel": "privacy@example.com",
                "retention_policy": "按最短必要期限保存",
            },
            "emergency_plan": {
                "incident_response_sla_hours": 72,
                "escalation_path": "隐私负责人 -> 法务 -> 管理层",
            },
            "attachments": [
                {
                    "file_role": "scc_contract",
                    "file_name": attachment_path.name,
                    "file_format": "txt",
                    "storage_uri": str(attachment_path),
                }
            ],
        }
    )


def _rag_documents() -> list[RegulationDoc]:
    return [
        RegulationDoc(
            id="CN-LAW-003",
            title="中华人民共和国个人信息保护法",
            article="第39条",
            content="向境外提供个人信息应告知境外接收方并取得个人的单独同意。",
            jurisdiction="cn",
            path="scc",
            source_url="https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm",
        ),
        RegulationDoc(
            id="CN-REG-010",
            title="个人信息出境标准合同办法",
            article="第6条",
            content="个人信息处理者应当在标准合同生效之日起十个工作日内备案。",
            jurisdiction="cn",
            path="scc",
            source_url="https://www.cac.gov.cn/2023-02/24/c_1678884830036813.htm",
        ),
    ]


def _patch_rag(monkeypatch) -> None:
    result = type("RetrievalResult", (), {"documents": _rag_documents()})()
    monkeypatch.setattr(
        "backend.domains.cn.pipia.service.retrieve_legal_documents",
        lambda *args, **kwargs: result,
    )


def test_no_llm_does_not_turn_rag_candidates_into_used_footnotes(
    monkeypatch, tmp_path: Path
) -> None:
    attachment = tmp_path / "case_evidence.txt"
    attachment.write_text("测试案例事实摘要，不是已经签署的标准合同。", encoding="utf-8")
    _patch_rag(monkeypatch)
    monkeypatch.chdir(tmp_path)

    service = PIPIAService(llm_client=None)
    service.renderer.schema_first_enabled = True
    result = service.generate_report(_payload(attachment), task_id="pipia-no-llm-citations")

    citation_map = json.loads(Path(result.output_files["citation_map_json"]).read_text())
    markdown = Path(result.output_files["markdown"]).read_text(encoding="utf-8")

    assert len(citation_map["all_items"]) == 2
    assert citation_map["footnote_map"] == {}
    assert not re.search(r"\[\d+\]", markdown)


def test_service_keeps_only_explicit_pipia_citations_in_all_output_layers(
    monkeypatch, tmp_path: Path
) -> None:
    attachment = tmp_path / "case_evidence.txt"
    attachment.write_text("测试案例事实摘要，不是已经签署的标准合同。", encoding="utf-8")
    _patch_rag(monkeypatch)
    monkeypatch.chdir(tmp_path)

    service = PIPIAService(llm_client=_FirstCitationLLM())
    service.renderer.schema_first_enabled = True
    result = service.generate_report(_payload(attachment), task_id="pipia-citation-sync")

    markdown = Path(result.output_files["markdown"]).read_text(encoding="utf-8")
    citation_map = json.loads(Path(result.output_files["citation_map_json"]).read_text())
    document_ir = json.loads(Path(result.output_files["document_ir_json"]).read_text())

    markdown_numbers = set(re.findall(r"\[(\d+)\]", markdown))
    map_numbers = set(citation_map["footnote_map"])
    map_citation_ids = {
        item["citation_id"] for item in citation_map["footnote_map"].values()
    }
    claim_refs = {
        citation_id
        for section in document_ir["sections"]
        for block in section["blocks"]
        for citation_id in block.get("citation_refs", [])
    }

    assert len(citation_map["all_items"]) == 2
    assert markdown_numbers == {"1"}
    assert map_numbers == markdown_numbers
    assert len(map_citation_ids) == 1
    assert claim_refs == map_citation_ids
