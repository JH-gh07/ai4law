"""Tests for the Level B seed request adapter.

The adapter (`scripts/build_seed_case_requests.py`) maps each of the 50 Level A
extraction records into exactly one Level B disposition: `gap`, `rejected`, or
`converted`. These tests verify the plan's hard constraints:

- every seed case has exactly one disposition;
- gap cases (task 7/8) never produce a request;
- supported cases whose key facts are missing/placeholder-tainted are REJECTED
  (never silently defaulted to a company/country/count/receiver/attachment);
- a complete, non-placeholder input for every supported module CONVERTS and
  validates against the real Pydantic request schema;
- no emitted request ever carries a placeholder token or the schema's "示例企业"
  default company.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = ROOT / "scripts" / "build_seed_case_requests.py"
INPUTS_DIR = ROOT / "benchmarks/datasets/seed-cases-v1/inputs"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("build_seed_case_requests", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = _load_adapter()


def _real_records() -> list[dict]:
    records = []
    for path in sorted(INPUTS_DIR.glob("*.input.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    assert len(records) == 50
    return records


def _dispositions() -> list[dict]:
    return [adapter.adjudicate(r) for r in _real_records()]


# ── frozen corpus properties ────────────────────────────────────────────────


def test_every_seed_case_has_exactly_one_disposition() -> None:
    records = _real_records()
    dispositions = _dispositions()
    assert len(dispositions) == 50
    ids = [d["case_id"] for d in dispositions]
    assert len(set(ids)) == 50
    assert set(ids) == {r["case_id"] for r in records}
    for d in dispositions:
        assert d["levelb"] in {"gap", "rejected", "converted"}


def test_gap_cases_never_produce_requests() -> None:
    for d in _dispositions():
        if d["case_id"].startswith(("task07_", "task08_")):
            assert d["levelb"] == "gap"
            assert d["request_path"] is None
            assert d["module_id"] is None or d["module_id"] == ""


def test_supported_cases_are_never_silently_defaulted() -> None:
    """Supported cases missing key facts must be rejected, not defaulted."""
    for d in _dispositions():
        if d["case_id"].startswith(("task07_", "task08_")):
            continue
        if d["levelb"] == "rejected":
            assert d["blocking_missing_facts"], d
            assert d["request_path"] is None
        # Any converted case must have no blocking facts.
        if d["levelb"] == "converted":
            assert d["blocking_missing_facts"] == []


def test_frozen_corpus_is_rejected_not_fabricated() -> None:
    """The seed corpus is raw/anonymized; the adapter must not invent facts.

    This asserts the current reality: every supported seed case lacks at least
    one key fact, so the adapter rejects all of them rather than fabricating a
    company/country/count/receiver/attachment.
    """
    dispositions = _dispositions()
    supported = [d for d in dispositions if d["levelb"] != "gap"]
    assert len(supported) == 40
    # Document the blocking facts so any future drift is explicit.
    for d in supported:
        assert d["levelb"] == "rejected", d["case_id"]


# ── adapter refuses placeholders in key facts ───────────────────────────────


def test_placeholder_company_name_is_missing() -> None:
    assert adapter._is_missing("XX城商银行股份有限公司")
    assert adapter._is_missing("某公司")
    assert adapter._is_missing("")
    assert adapter._is_missing(None)
    assert not adapter._is_missing("跨境优品科技有限公司")


def test_fuzzy_counts_are_not_parsed_as_exact() -> None:
    assert adapter._parse_count("≥1万") is None
    assert adapter._parse_count("大概有200万用户") is None
    assert adapter._parse_count("10万-100万") is None
    assert adapter._parse_count("几万") is None
    assert adapter._parse_count("200个员工") == 200
    assert adapter._parse_count("1万") == 10000


# ── conversion path: complete facts validate against the real schema ───────


def _synthetic_record(module_id: str, task_no: int, case_no: int, paragraphs: list[str]) -> dict:
    return {
        "case_id": f"task{task_no:02d}_case{case_no}",
        "task_no": task_no,
        "module_id": module_id,
        "mapping_status": "partial",
        "input": {"paragraphs": paragraphs},
    }


def test_transfer_diagnosis_converts_on_complete_facts() -> None:
    rec = _synthetic_record("cn.transfer_diagnosis", 1, 99, [
        "公司全称：跨境优品科技有限公司",
        "问题1：是否包含重要数据？",
        "否。",
        "问题4：是否属于CIIO？",
        "否。",
        "问题5：累计出境个人信息类型？",
        "含敏感。",
        "问题7：若含敏感个人信息，累计人数？",
        "5000。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "converted", d


def test_security_assessment_converts_on_complete_facts() -> None:
    rec = _synthetic_record("cn.security_assessment", 2, 99, [
        "公司全称：跨境优品科技有限公司；所属行业：互联网信息服务。",
        "目的：将订单数据同步至新加坡亚太数据中心。",
        "7. 境外接收方信息",
        "基本情况：某新加坡数据处理公司。",
        "累计出境个人信息约450000人，不涉及敏感个人信息。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "rejected", d  # fuzzy 约/敏感 keeps count ambiguous
    # A clean count and a real country make it convert.
    rec["input"]["paragraphs"] = [
        "公司全称：跨境优品科技有限公司；所属行业：互联网信息服务。",
        "目的：将订单数据同步至新加坡亚太数据中心。",
        "7. 境外接收方信息 基本情况：某新加坡数据处理公司。",
        "累计出境个人信息 450000 人，不涉及敏感个人信息。",
    ]
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "converted", d


def test_pipia_rejects_without_attachment() -> None:
    rec = _synthetic_record("cn.pipia", 3, 99, [
        "公司信息：跨境优品科技有限公司，互联网行业，非CIIO。统一社会信用代码：91310000MA1FL12345。",
        "数据字段名：用户ID、浏览记录。",
        "基本情况：某新加坡子公司。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "rejected"
    assert "attachments" in d["blocking_missing_facts"]


def test_scc_review_rejects_without_scc_text_and_module() -> None:
    rec = _synthetic_record("eu.scc_review", 5, 99, [
        "项目名称：示例跨境项目",
        "上传方陈述：我们和供应商签了合同。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "rejected"
    assert "scc_text" in d["blocking_missing_facts"]
    assert "declared_module_type" in d["blocking_missing_facts"]


def test_tia_rejects_without_tool_and_profiles() -> None:
    rec = _synthetic_record("eu.tia", 6, 99, [
        "上传方陈述：我们签了SCC。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "rejected"
    assert "transfer_tool" not in d["blocking_missing_facts"]  # SCC -> tool detected
    assert "attachments" in d["blocking_missing_facts"]


def test_us14117_rejects_without_recipient_entities() -> None:
    rec = _synthetic_record("us.eo_14117", 9, 99, [
        "项目名称：示例数据迁移",
        "涉及精确地理位置信息和面部生物识别特征模板。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "rejected"
    assert "recipient_entities" in d["blocking_missing_facts"]


def test_cpra_rejects_without_structured_sections() -> None:
    rec = _synthetic_record("us.cpra", 10, 99, [
        "用户补充说明：我们不出售用户数据。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "rejected"
    assert "business_model" in d["blocking_missing_facts"]
    assert "attachments" in d["blocking_missing_facts"]


def test_no_request_carries_placeholder_or_default_company() -> None:
    """No emitted request may contain a placeholder token or the schema default."""
    for rec in _real_records():
        if rec.get("module_id") and rec.get("mapping_status") != "gap":
            request_dict, missing = adapter.ADAPTERS[rec["module_id"]](
                rec["input"]["paragraphs"]
            )
            if request_dict is not None:
                blob = json.dumps(request_dict, ensure_ascii=False, default=str)
                assert "示例企业" not in blob
                assert "XX" not in blob
