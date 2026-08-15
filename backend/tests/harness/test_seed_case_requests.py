"""Tests for the Level B seed request adapter.

The adapter (`scripts/build_seed_case_requests.py`) maps each of the 50 Level A
extraction records into exactly one Level B disposition: `gap`, `rejected`,
`converted`, or `pending_correction`. These tests verify the plan's hard
constraints:

- every seed case has exactly one disposition;
- v2.0 校正后 gap 归零（task4/6/7/8 均有对应模块）；
- 12 个 pending_correction case（task4/6/7/8 case3/4/5）被隔离，不产 request；
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
        assert d["levelb"] in {"gap", "rejected", "converted", "pending_correction"}


def test_no_gap_cases_after_v2_0_correction() -> None:
    """v2.0 校正后 task4/6/7/8 均有对应模块，gap 归零。"""
    dispositions = _dispositions()
    assert not any(d["levelb"] == "gap" for d in dispositions)


def test_pending_correction_cases_are_isolated_no_requests() -> None:
    """12 个 v1.0 旧内容 case 被隔离，不进入 request 路径。"""
    pending = [d for d in _dispositions() if d["levelb"] == "pending_correction"]
    assert len(pending) == 12
    assert {d["case_id"] for d in pending} == {
        f"task{tn:02d}_case{c}"
        for tn in (4, 6, 7, 8)
        for c in (3, 4, 5)
    }
    for d in pending:
        assert d["request_path"] is None
        assert d["blocking_missing_facts"] == []


def test_supported_cases_are_never_silently_defaulted() -> None:
    """Supported cases missing key facts must be rejected, not defaulted."""
    for d in _dispositions():
        if d["levelb"] == "rejected":
            assert d["blocking_missing_facts"], d
            assert d["request_path"] is None
        # Any converted case must have no blocking facts.
        if d["levelb"] == "converted":
            assert d["blocking_missing_facts"] == []


def test_frozen_corpus_rejected_or_isolated_not_fabricated() -> None:
    """The raw/anonymized corpus is never silently defaulted.

    v2.0 校正后现状：12 个 pending_correction 隔离，29 个缺关键事实被 rejected，
    9 个事实完整可 converted（task02_case4 及 task04/06 附件派生、task07 DPIA、
    task08 TIA）。
    """
    dispositions = _dispositions()
    tally: dict[str, int] = {}
    for d in dispositions:
        tally[d["levelb"]] = tally.get(d["levelb"], 0) + 1
    assert tally == {"rejected": 29, "pending_correction": 12, "converted": 9}
    # Document the blocking facts so any future drift is explicit.
    for d in dispositions:
        if d["levelb"] == "rejected":
            assert d["blocking_missing_facts"], d["case_id"]
        elif d["levelb"] == "converted":
            assert d["blocking_missing_facts"] == [], d["case_id"]


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


def test_parse_count_extracts_explicit_figure_after_range_prefix() -> None:
    """「<1万。5000人」中 <1万 模糊但 5000 是明确数字，应提取 5000。"""
    assert adapter._parse_count("<1万。5000人的全基因组数据。") == 5000
    assert adapter._parse_count("≥1万。粗略算一下大概有200万用户的数据都在传。") is None


def test_parse_ynu_negative_matches_before_positive() -> None:
    """否定词必须先于肯定词命中，否则「不属于/不包含/不含」会被误判为 yes。"""
    assert adapter._parse_ynu("不属于CIIO") == "no"
    assert adapter._parse_ynu("不包含敏感信息") == "no"
    assert adapter._parse_ynu("不含敏感个人信息") == "no"
    assert adapter._parse_ynu("否。我们是民营医疗AI公司。") == "no"
    assert adapter._parse_ynu("含敏感。基因组数据应该算敏感的。") == "yes"
    assert adapter._parse_ynu("属于重要数据") == "yes"


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


def test_tia_rejects_without_structured_facts() -> None:
    rec = _synthetic_record("eu.tia", 6, 99, [
        "上传方陈述：我们签了SCC。",
    ])
    d = adapter.adjudicate(rec)
    assert d["levelb"] == "rejected"
    assert "transfer_tool" not in d["blocking_missing_facts"]  # SCC -> tool detected
    # B2：旧表单结论/附件字段不再 blocking；结构化事实缺失才 blocking。
    assert "attachments" not in d["blocking_missing_facts"]
    assert "final_conclusion" not in d["blocking_missing_facts"]
    assert "third_country_assessment" not in d["blocking_missing_facts"]
    assert {"data_categories", "exporter_country", "importer_country", "transfer_purpose"} <= set(
        d["blocking_missing_facts"]
    )


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
            fn = adapter.ADAPTERS[rec["module_id"]]
            paras = rec["input"]["paragraphs"]
            if rec["module_id"] in ("cn.document_review", "eu.bcr_review"):
                request_dict, _ = fn(
                    paras,
                    source_docx=rec.get("source_docx") or "",
                    source_sha256=rec.get("source_sha256") or "",
                )
            else:
                request_dict, _ = fn(paras)
            if request_dict is not None:
                blob = json.dumps(request_dict, ensure_ascii=False, default=str)
                assert "示例企业" not in blob
                assert "XX" not in blob


# ── source-fidelity (request ↔ source paragraph) regressions ────────────────


def _converted_request(case_id: str) -> dict:
    path = INPUTS_DIR / f"{case_id}.input.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    fn = adapter.ADAPTERS[rec["module_id"]]
    paras = rec["input"]["paragraphs"]
    if rec["module_id"] in ("cn.document_review", "eu.bcr_review"):
        request_dict, _ = fn(
            paras,
            source_docx=rec.get("source_docx") or "",
            source_sha256=rec.get("source_sha256") or "",
        )
    else:
        request_dict, _ = fn(paras)
    assert request_dict is not None, case_id
    return request_dict


def test_dpia_converted_requests_match_source_facts() -> None:
    """task07 DPIA 不得再出现「原文有、request 却 false/空」的反向声明。"""
    req1 = _converted_request("task07_case1")
    assert req1["special_category_data"] is True
    assert req1["vulnerable_data_subjects"] is True
    assert req1["cross_border_transfer"] is True
    assert req1["data_categories"]
    assert req1["lawful_basis"]
    assert req1["retention_period"]
    assert "以色列" in req1["transfer_destination"]
    assert "MediAssist" in req1["project_name"]

    req2 = _converted_request("task07_case2")
    assert req2["special_category_data"] is False  # 源文明确「声称不涉及特殊类别」
    assert req2["cross_border_transfer"] is True  # 源文有供应商远程访问
    assert req2["data_categories"]
    assert "FacePass" in req2["project_name"]


def test_tia_converted_requests_use_structured_input() -> None:
    """task08 TIA 走 structured_input，结论字段不再当 input 伪造。"""
    req1 = _converted_request("task08_case1")
    si1 = req1["structured_input"]
    assert si1["importer_country"] == "India"
    assert si1["has_special_category_data"] is True
    assert si1["data_categories"]
    assert req1["final_conclusion"] == ""
    assert req1["third_country_assessment"] == ""

    req2 = _converted_request("task08_case2")
    si2 = req2["structured_input"]
    assert si2["importer_country"] == "United States"
    assert si2["has_end_to_end_encryption"] is False  # 源文「未实施端到端加密」
    assert si2["encryption_before_transfer"] is True


def test_attachment_driven_requests_reference_real_files() -> None:
    """task04/06 的附件派生必须指向 storage 中真实存在的文件。"""
    for case_id in ("task04_case1", "task04_case2"):
        req = _converted_request(case_id)
        for uri in req["uploaded_files"]:
            assert (adapter.ROOT / uri).is_file(), uri
    for case_id in ("task06_case1", "task06_case2"):
        req = _converted_request(case_id)
        assert req["uploaded_documents"], case_id
        for doc in req["uploaded_documents"]:
            assert (adapter.ROOT / doc["file_path"]).is_file(), doc["file_path"]
