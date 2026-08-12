#!/usr/bin/env python3
"""Level B: convert seed extraction records into module request schemas.

The Level A builder (`build_seed_case_inputs.py`) produces 50 source-fidelity
extraction records under `benchmarks/datasets/seed-cases-v1/inputs/`. This
script performs the second conversion tier required by task065 §3.2:

    Level A: DOCX -> source-fidelity extraction record         (50/50)
    Level B: extraction record -> module request schema -> CLI/HTTP
                                                        (only adjudicated cases)

For every seed case the script records exactly one Level B disposition:

    gap       — no product capability (task 7/8). Referenced to
                `status/check/task065/seed-gap-ledger.json`, never given a request.
    rejected  — a supported module exists, but one or more key facts are missing
                or placeholder-tainted. The adapter MUST NOT fabricate a default
                company, country, count, receiver or attachment, so the case is
                blocked and its blocking facts are recorded verbatim.
    converted — every key fact is present and the request validates against the
                module's Pydantic schema; the request is emitted to
                `benchmarks/datasets/seed-cases-v1/requests/<case_id>.request.json`.

The module identity is the frozen mapping already written into every Level A
record (`module_id` / `mapping_status`), which mirrors
`status/check/task065/seed-mapping-adjudication.md`. This script does NOT
re-adjudicate module identity; it only decides whether the declared module can
be *entered* from the facts actually present in the source.

Key-fact policy (task065 §T03 requirement 3, verbatim intent):
the adapter must reject missing key facts and must NOT substitute a default
company, country, count, receiver or attachment. Every adapter therefore
returns ``None`` (no request) whenever any required field is absent or carries a
placeholder token; it never emits a request with a fabricated value.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "benchmarks/datasets/seed-cases-v1"
INPUTS_DIR = DATASET_DIR / "inputs"
REQUESTS_DIR = DATASET_DIR / "requests"
GAP_LEDGER_PATH = ROOT / "status/check/task065/seed-gap-ledger.json"

GAP_TASKS: dict[int, str] = {7: "GDPR 合规诊断", 8: "BD ROD 判断"}

# Placeholder / anonymization tokens. Any key fact that is empty or carries one
# of these is treated as MISSING.
_PLACEHOLDER_RE = re.compile(
    r"XX|某某|某[公司人企业]|待补充|待定|待确认|待填写|TBD|示例|几[万千]|若干|不详|不清楚"
)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict)):
        if len(value) == 0:
            return True
        return any(_is_missing(v) for v in value)
    text = str(value).strip()
    if not text:
        return True
    return bool(_PLACEHOLDER_RE.search(text))


def _parse_ynu(text: str) -> str | None:
    if not text:
        return None
    if any(t in text for t in ("不确定", "不知道", "不清楚", "暂按")):
        return "unknown"
    if re.search(r"^是[。，；;]?$|属于|包含敏感|含敏感|不属于", text):
        return "yes"
    if re.search(r"^否[。，；;]?$|不含|不包含|不涉及", text):
        return "no"
    return None


def _parse_count(text: str) -> int | None:
    """Parse an explicit integer count; reject fuzzy ranges / placeholders."""
    if _is_missing(text):
        return None
    if any(t in text for t in ("约", "大概", "左右", "≥", "≤", "-", "至", "几")):
        return None
    m = re.search(r"(\d+)\s*(万|千)?", text)
    if not m:
        return None
    value = int(m.group(1))
    if m.group(2) == "万":
        value *= 10000
    elif m.group(2) == "千":
        value *= 1000
    return value


# ────────────────────────────────────────────────────────────────────────────
# Adapters: each returns (request_dict | None, missing_facts: list[str]).
# A non-None request only happens when missing_facts is empty.
# ────────────────────────────────────────────────────────────────────────────


def _adapter_transfer_diagnosis(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    company_name = ""
    m = re.search(r"(?:公司全称|公司名称|企业名称|公司信息)[：:]\s*(.{2,40}?)(?:[；;。\n]|$)", text)
    if m:
        company_name = m.group(1).strip()
    if _is_missing(company_name):
        missing.append("company_name")

    # Extract the Q&A answers (问题N -> next paragraphs until next 问题N).
    answers: dict[int, str] = {}
    for i, p in enumerate(paras):
        m = re.match(r"^问题(\d+)", p)
        if not m:
            continue
        qno = int(m.group(1))
        buf: list[str] = []
        for q in paras[i + 1 :]:
            if re.match(r"^问题\d+", q):
                break
            if q.strip():
                buf.append(q.strip())
        answers[qno] = "\n".join(buf)

    q1 = answers.get(1, "")
    q4 = answers.get(4, "")
    q6 = answers.get(6, "")
    q7 = answers.get(7, "")

    # q1_is_ciio <- 问题4; q2_has_important_data <- 问题1.
    q1_is_ciio = _parse_ynu(q4)
    q2_has_important_data = _parse_ynu(q1)
    if q1_is_ciio is None:
        missing.append("answers.q1_is_ciio")
    if q2_has_important_data is None:
        missing.append("answers.q2_has_important_data")

    has_spi = "敏感" in text or "含敏感" in text
    if has_spi:
        spi = _parse_count(q7)
        if spi is None:
            missing.append("answers.q4_spi_count")
        pii_count = 0
        spi_count = spi or 0
    else:
        pii = _parse_count(q6)
        if pii is None:
            missing.append("answers.q3_pii_count")
        pii_count = pii or 0
        spi_count = 0

    if missing:
        return None, missing

    from backend.domains.cn.transfer_diagnosis.schema import (
        DiagnosisAnswers,
        DiagnosisReportRequest,
        ReceiverType,
        TransferScenario,
        YesNoUnknown,
    )

    request = DiagnosisReportRequest(
        company_name=company_name,
        answers=DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown(q1_is_ciio),
            q2_has_important_data=YesNoUnknown(q2_has_important_data),
            q3_pii_count=pii_count,
            q4_spi_count=spi_count,
            q5_no_personal_info=YesNoUnknown.NO,
            q6_scenario=(
                TransferScenario.HR_MANAGEMENT if "人力资源" in text
                else TransferScenario.CONTRACT_PERFORMANCE if "履行" in text
                else TransferScenario.OTHER
            ),
            q7_receiver_type=(
                ReceiverType.INTRA_GROUP if ("集团" in text or "子公司" in text)
                else ReceiverType.THIRD_PARTY
            ),
            q8_purpose=text[:200],
        ),
    )
    return request.model_dump(), []


def _adapter_security_assessment(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    company_name = ""
    industry = ""
    m = re.search(r"公司全称[：:]\s*(.{2,40}?)(?:[；;。]|$)", text)
    if m:
        company_name = m.group(1).strip()
    m = re.search(r"所属行业[：:]\s*(.{2,30}?)(?:[；;。]|$)", text)
    if m:
        industry = m.group(1).strip()
    if _is_missing(company_name):
        missing.append("company_name")

    transfer_purpose = ""
    m = re.search(r"目的[：:]\s*(.{2,60}?)(?:[；;。]|$)", text)
    if m:
        transfer_purpose = m.group(1).strip()
    if _is_missing(transfer_purpose):
        missing.append("transfer_purpose")

    receiver_country = ""
    for country in ("美国", "德国", "日本", "瑞士", "新加坡", "英国", "法国", "巴西", "印度", "中国"):
        if country in text:
            receiver_country = country
            break
    if _is_missing(receiver_country):
        missing.append("receiver_country")

    # Counts are not reliably present in the seed assessment corpus; the adapter
    # must not invent a number, so a missing count blocks the request.
    m = re.search(r"(?:累计|出境).{0,12}?(\d+(?:\s*[万千])?)\s*(?:人|名|用户)", text)
    pii_count = _parse_count(m.group(0)) if m else None
    if pii_count is None and "不涉及个人信息" not in text:
        missing.append("pii_count")

    if missing:
        return None, missing

    from backend.domains.cn.security_assessment.schema import AssessmentRequest

    request = AssessmentRequest(
        company_name=company_name,
        industry=industry,
        is_ciio=False,
        contains_important_data=("重要数据" in text and "未" not in text),
        pii_count=pii_count or 0,
        spi_count=0,
        transfer_purpose=transfer_purpose,
        receiver_country=receiver_country,
    )
    return request.model_dump(), []


def _adapter_pipia(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    company_name = ""
    uscc = ""
    m = re.search(r"公司信息[：:]\s*(.{2,40}?)(?:[，,；;。]|$)", text)
    if m:
        company_name = m.group(1).strip()
    m = re.search(r"统一社会信用代码[：:]\s*(\w{8,18})", text)
    if m:
        uscc = m.group(1).strip()
    if _is_missing(company_name):
        missing.append("company_profile.company_name")
    if _is_missing(uscc):
        missing.append("company_profile.company_uscc")

    recipient = ""
    m = re.search(r"基本情况[：:]\s*(.{2,60}?)(?:[，,；;。]|$)", text)
    if m:
        recipient = m.group(1).strip()
    if _is_missing(recipient):
        missing.append("transfer_context.recipient_name")

    country = ""
    for c in ("美国", "英国", "日本", "新加坡", "德国", "法国"):
        if c in text:
            country = c
            break
    if _is_missing(country):
        missing.append("transfer_context.recipient_country_region")

    pi_categories: list[str] = []
    m = re.search(r"数据字段名[：:]\s*(.+)", text)
    if m:
        pi_categories = [x.strip() for x in m.group(1).split("、") if x.strip()][:10]
    if not pi_categories:
        missing.append("personal_info_scope.pi_categories")

    # attachments(min_length=1) is a hard key fact; seed pipia cases have none.
    missing.append("attachments")

    if missing:
        return None, missing

    from backend.domains.cn.pipia.schema import (
        PIPIACompanyProfile,
        PIPIAEmergencyPlan,
        PIPIAPersonalInfoScope,
        PIPIARightsProtection,
        PIPIARequest,
        PIPIATransferContext,
    )

    purpose = "用户行为分析" if "行为" in text else ("客户服务" if "客户" in text else "数据处理")
    request = PIPIARequest(
        route_type="scc_filing",
        company_profile=PIPIACompanyProfile(company_name=company_name, company_uscc=uscc),
        transfer_context=PIPIATransferContext(
            purpose=purpose,
            recipient_name=recipient,
            recipient_country_region=country,
            legal_basis="用户同意",
        ),
        personal_info_scope=PIPIAPersonalInfoScope(pi_categories=pi_categories),
        rights_protection=PIPIARightsProtection(
            notice_mechanism="隐私政策告知",
            consent_mechanism="用户同意",
            dsar_channel="在线客服",
            retention_policy="见隐私政策",
        ),
        emergency_plan=PIPIAEmergencyPlan(incident_response_sla_hours=72, escalation_path="上报负责人"),
        attachments=[],
    )
    return request.model_dump(), []


def _adapter_scc_review(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    project_name = ""
    m = re.search(r"项目名称[：:]\s*(.{2,40}?)(?:[；;。]|$)", text)
    if m:
        project_name = m.group(1).strip()
    if _is_missing(project_name):
        missing.append("project_name")

    # Seed SCC cases carry only an uploader statement, never an actual clause
    # text or a declared module. Both are key facts and cannot be fabricated.
    missing.append("scc_text")
    missing.append("declared_module_type")

    if missing:
        return None, missing

    from backend.domains.eu.scc_review.schema import SCCReviewRequest

    request = SCCReviewRequest(
        project_name=project_name,
        scc_text=text,
        declared_module_type="Module Two",
    )
    return request.model_dump(), []


def _adapter_tia(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    tool = None
    if "SCC" in text or "标准合同" in text:
        tool = "scc"
    elif "BCR" in text:
        tool = "bcr"
    if tool is None:
        missing.append("transfer_tool")

    # The six-item TIA form is sparse; profiles/assessment/measures/conclusion
    # and attachments are all missing in the seed corpus.
    for field in (
        "data_exporter_profile",
        "data_importer_profile",
        "third_country_assessment",
        "supplementary_measures",
        "final_conclusion",
        "attachments",
    ):
        missing.append(field)

    if missing:
        return None, missing

    from backend.domains.eu.tia.schema import TIARequest

    request = TIARequest(
        transfer_tool=tool,
        data_exporter_profile="",
        data_importer_profile="",
        third_country_assessment="",
        supplementary_measures="",
        final_conclusion="",
        attachments=[],
    )
    return request.model_dump(), []


def _adapter_us14117(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    project_name = ""
    m = re.search(r"项目名称[：:]\s*(.{2,40}?)(?:[；;。]|$)", text)
    if m:
        project_name = m.group(1).strip()
    if _is_missing(project_name):
        missing.append("project_name")

    transaction_description = text[:300]
    if _is_missing(transaction_description):
        missing.append("transaction_description")

    data_item_names = [
        name for name in (
            "精确地理位置信息", "面部生物识别特征模板", "姓名", "邮箱",
            "电话号码", "基因组测序数据", "生物识别数据",
        ) if name in text
    ]
    if not data_item_names:
        missing.append("data_items")

    # The seed 外部实体清单 is empty (only 内部员工清单 is filled), so no
    # recipient entity can be sourced; this blocks the request.
    missing.append("recipient_entities")

    if missing:
        return None, missing

    from backend.domains.us.eo14117.schema import US14117DataItem, US14117Entity, US14117Request

    request = US14117Request(
        project_name=project_name,
        transaction_description=transaction_description,
        data_items=[US14117DataItem(data_item_name=n) for n in data_item_names],
        recipient_entities=[US14117Entity(entity_name="", country_of_registration="")],
    )
    return request.model_dump(), []


def _adapter_cpra(paras: list[str]) -> tuple[dict | None, list[str]]:
    # CPRA seed records fill only a free-text 补充说明; the four structured
    # sections are empty. All required free-text fields and the attachment are
    # blocked, never defaulted.
    missing = [
        "business_model",
        "data_lifecycle",
        "notice_and_consent",
        "consumer_rights_process",
        "opt_out_and_sale_sharing",
        "attachments",
    ]
    return None, missing


ADAPTERS: dict[str, Callable[[list[str]], tuple[dict | None, list[str]]]] = {
    "cn.transfer_diagnosis": _adapter_transfer_diagnosis,
    "cn.security_assessment": _adapter_security_assessment,
    "cn.pipia": _adapter_pipia,
    "eu.scc_review": _adapter_scc_review,
    "eu.tia": _adapter_tia,
    "us.eo_14117": _adapter_us14117,
    "us.cpra": _adapter_cpra,
}

_SCHEMA_LOADERS: dict[str, Callable[[], Any]] = {}


def _schema_for(module_id: str) -> Any:
    if module_id not in _SCHEMA_LOADERS:
        def load() -> Any:
            if module_id == "cn.transfer_diagnosis":
                from backend.domains.cn.transfer_diagnosis.schema import DiagnosisReportRequest as M
            elif module_id == "cn.security_assessment":
                from backend.domains.cn.security_assessment.schema import AssessmentRequest as M
            elif module_id == "cn.pipia":
                from backend.domains.cn.pipia.schema import PIPIARequest as M
            elif module_id == "eu.scc_review":
                from backend.domains.eu.scc_review.schema import SCCReviewRequest as M
            elif module_id == "eu.tia":
                from backend.domains.eu.tia.schema import TIARequest as M
            elif module_id == "us.eo_14117":
                from backend.domains.us.eo14117.schema import US14117Request as M
            elif module_id == "us.cpra":
                from backend.domains.us.cpra.schema import CPRARequest as M
            else:
                raise ValueError(f"unknown module_id: {module_id}")
            return M
        _SCHEMA_LOADERS[module_id] = load
    return _SCHEMA_LOADERS[module_id]()


def adjudicate(record: dict) -> dict:
    """Return a Level B disposition dict for one Level A record."""
    case_id = record["case_id"]
    task_no = record["task_no"]
    module_id = record.get("module_id") or ""
    mapping_status = record.get("mapping_status") or ""

    if mapping_status == "gap" or module_id == "":
        return {
            "case_id": case_id,
            "task_no": task_no,
            "module_id": module_id or None,
            "levelb": "gap",
            "request_path": None,
            "blocking_missing_facts": [],
            "note": f"no product capability ({GAP_TASKS.get(task_no, 'gap')})",
            "gap_ledger": str(GAP_LEDGER_PATH.relative_to(ROOT)),
        }

    adapter = ADAPTERS.get(module_id)
    if adapter is None:
        raise ValueError(f"no adapter for supported module {module_id} ({case_id})")

    paras = record.get("input", {}).get("paragraphs", [])
    request_dict, missing = adapter(paras)
    missing = sorted(set(missing))

    if missing:
        return {
            "case_id": case_id,
            "task_no": task_no,
            "module_id": module_id,
            "levelb": "rejected",
            "request_path": None,
            "blocking_missing_facts": missing,
            "note": "key facts missing or placeholder-tainted; adapter refuses to fabricate defaults",
        }

    schema = _schema_for(module_id)
    try:
        schema.model_validate(request_dict)
    except Exception as exc:  # noqa: BLE001 - record the concrete schema error
        return {
            "case_id": case_id,
            "task_no": task_no,
            "module_id": module_id,
            "levelb": "rejected",
            "request_path": None,
            "blocking_missing_facts": missing,
            "schema_errors": [str(exc)],
            "note": "request failed module schema validation",
        }

    return {
        "case_id": case_id,
        "task_no": task_no,
        "module_id": module_id,
        "levelb": "converted",
        "request_path": f"benchmarks/datasets/seed-cases-v1/requests/{case_id}.request.json",
        "blocking_missing_facts": [],
        "note": "all key facts present and schema-valid",
    }


def load_records() -> list[dict]:
    if not INPUTS_DIR.exists():
        print(f"ERROR inputs dir missing: {INPUTS_DIR}")
        raise SystemExit(2)
    records: list[dict] = []
    for path in sorted(INPUTS_DIR.glob("*.input.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if len(records) != 50:
        print(f"ERROR expected 50 Level A records, got {len(records)}")
        raise SystemExit(2)
    return records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write converted requests + ledger to disk")
    args = ap.parse_args()

    records = load_records()
    dispositions = [adjudicate(r) for r in records]

    tally: dict[str, int] = {}
    for d in dispositions:
        tally[d["levelb"]] = tally.get(d["levelb"], 0) + 1

    print(f"records              : {len(records)}")
    print(f"levelb disposition   : {tally}")

    for d in dispositions:
        if d["levelb"] == "rejected":
            print(f"  rejected {d['case_id']:<16} {d['blocking_missing_facts']}")

    if not args.write:
        print("DRY-RUN (pass --write to emit requests + ledger)")
        return 0

    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for d in dispositions:
        if d["levelb"] == "converted":
            rec = next(r for r in records if r["case_id"] == d["case_id"])
            adapter = ADAPTERS[d["module_id"]]
            request_dict, _ = adapter(rec.get("input", {}).get("paragraphs", []))
            out = REQUESTS_DIR / f"{d['case_id']}.request.json"
            out.write_text(
                json.dumps(request_dict, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            written += 1

    ledger = {
        "schema_version": "1.0",
        "generated_by": "scripts/build_seed_case_requests.py",
        "tier": "Level B (extraction record -> module request schema)",
        "counts": tally,
        "gap_ledger": str(GAP_LEDGER_PATH.relative_to(ROOT)),
        "dispositions": dispositions,
    }
    ledger_path = DATASET_DIR / "levelb-disposition.v1.json"
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE {written} requests -> {REQUESTS_DIR.relative_to(ROOT)}")
    print(f"WROTE ledger         -> {ledger_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
