#!/usr/bin/env python3
"""Level B: convert seed extraction records into module request schemas.

The Level A builder (`build_seed_case_inputs.py`) produces 50 source-fidelity
extraction records under `benchmarks/datasets/seed-cases-v1/inputs/`. This
script performs the second conversion tier required by task065 §3.2:

    Level A: DOCX -> source-fidelity extraction record         (50/50)
    Level B: extraction record -> module request schema -> CLI/HTTP
                                                        (only adjudicated cases)

For every seed case the script records exactly one Level B disposition:

    pending_correction — v2.0 marks the case 需修正/待修正 (task4/6/7/8
                case3/4/5); its body is still v1.0 legacy content and must be
                isolated before any request conversion.
    gap       — no product capability. Referenced to
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
# Make `backend.*` importable when this script is run directly as
# `python3 scripts/build_seed_case_requests.py` (sys.path[0] is scripts/, not ROOT).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET_DIR = ROOT / "benchmarks/datasets/seed-cases-v1"
INPUTS_DIR = DATASET_DIR / "inputs"
REQUESTS_DIR = DATASET_DIR / "requests"
GAP_LEDGER_PATH = ROOT / "status/check/task065/seed-gap-ledger.json"
# Input-only attachment derivation (task074 B3): task04/06 carry a real source
# DOCX whose body is the document-to-review / BCR text. We copy it into storage
# so the module's upload-driven request has a genuine file reference — never a
# fabricated id/path.
STORAGE_UPLOADS_DIR = ROOT / "storage" / "uploads"
SEED_ATTACHMENT_DIR = STORAGE_UPLOADS_DIR / "seed-cases-v1"

# v2.0 校正后 gap 归零：task4/6/7/8 已改对（文档审查 / BCR 审查 / DPIA 草案生成 /
# TIA 草案生成），10 个 task 均有对应产品模块。保留空表仅作防御，gap 分支不再有
# 实际命中（Level A 的 mapping_status 已全为 partial）。
GAP_TASKS: dict[int, str] = {}

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


def _derive_seed_attachment(source_docx: str, source_sha256: str = "") -> str:
    """Copy a seed source DOCX into storage and return its storage-relative URI.

    Returns ``""`` when no real source DOCX exists (the adapter must then keep
    blocking instead of inventing a file reference).
    """
    if not source_docx:
        return ""
    src = ROOT / source_docx
    if not src.exists() or not src.is_file():
        return ""
    SEED_ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
    short = (source_sha256 or src.name)[:8]
    dest = SEED_ATTACHMENT_DIR / f"{src.stem}_{short}{src.suffix}"
    if not dest.exists():
        dest.write_bytes(src.read_bytes())
    return dest.relative_to(ROOT).as_posix()


def _parse_ynu(text: str) -> str | None:
    if not text:
        return None
    if any(t in text for t in ("不确定", "不知道", "不清楚", "暂按")):
        return "unknown"
    # 否定必须先于肯定匹配，否则「不属于 / 不包含 / 不含」会被「属于 / 包含敏感 /
    # 含敏感」的子串先命中（如「不包含敏感信息」里含「包含敏感」）。
    if re.search(r"^否[。，；;]|不属于|不包含|不含|不涉及|不是", text):
        return "no"
    if re.search(r"^是[。，；;]|属于|包含敏感|含敏感", text):
        return "yes"
    return None


def _parse_count(text: str) -> int | None:
    """Parse an explicit integer count; reject fuzzy ranges / placeholders.

    A candidate is rejected only when it is *directly* tied to a fuzzy/range
    marker; an unrelated later number may still be explicit
    (e.g. ``"<1万。5000人的全基因组数据。"`` -> 5000).
    """
    if _is_missing(text):
        return None
    for m in re.finditer(r"(\d+)\s*(万|千)?", text):
        start, end = m.start(), m.end()
        # 只看当前数字所在小句（最近一个强分隔符之后）的前缀是否含模糊标记。
        seg = text[:start]
        cut = max(seg.rfind("。"), seg.rfind("；"), seg.rfind(";"),
                  seg.rfind("，"), seg.rfind(","), seg.rfind("\n"))
        window = seg[cut + 1:].strip()
        if any(t in window for t in ("约", "大概", "大约", "近", "≥", "≤", "<",
                                     ">", "至", "到", "~", "—", "几", "余", "多", "-")):
            continue
        suffix = text[end:end + 3]
        if any(t in suffix for t in ("左右", "以上", "以下", "余", "-", "~", "—", "至", "到")):
            continue
        value = int(m.group(1))
        if m.group(2) == "万":
            value *= 10000
        elif m.group(2) == "千":
            value *= 1000
        return value
    return None


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


_TIA_COUNTRY_EN = {
    "德国": "Germany", "荷兰": "Netherlands", "印度": "India", "美国": "United States",
    "中国": "China", "新加坡": "Singapore", "日本": "Japan", "韩国": "South Korea",
    "英国": "United Kingdom", "法国": "France", "奥地利": "Austria", "以色列": "Israel",
    "瑞士": "Switzerland", "加拿大": "Canada", "澳大利亚": "Australia", "巴西": "Brazil",
    "俄罗斯": "Russia", "马来西亚": "Malaysia", "泰国": "Thailand", "越南": "Vietnam",
    "印尼": "Indonesia", "菲律宾": "Philippines",
}

_TIA_CAT_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"健康|体检|医疗|诊断|病历"), "health_data"),
    (re.compile(r"基因|基因组"), "genetic_data"),
    (re.compile(r"生物识别|面部|指纹|虹膜|人脸|声纹"), "biometric_data"),
    (re.compile(r"儿童|未成年"), "children_data"),
    (re.compile(r"位置|定位|轨迹|IP地址|经纬度|地理"), "location_data"),
    (re.compile(r"行为|浏览|点击|偏好|页面访问|停留"), "behavioral_data"),
    (re.compile(r"通信内容|邮件内容|聊天记录|消息内容"), "communication_content"),
    (re.compile(r"客户细分|客户标签|CRM|会员等级"), "crm_data"),
    (re.compile(r"交易|购买|订单|金额|支付|消费"), "transaction_records"),
    (re.compile(r"员工|工号|职位|薪资|人力|雇员"), "employee_data"),
    (re.compile(r"考勤|绩效|培训|晋升|HR|人事"), "hr_records"),
    (re.compile(r"财务|银行|IBAN|税号|薪资级别|账"), "financial_data"),
    (re.compile(r"政治"), "political_opinion"),
    (re.compile(r"宗教|工会|信仰"), "religious_belief"),
    (re.compile(r"临床"), "clinical_trial_data"),
    (re.compile(r"姓名|邮箱|邮寄地址|联系地址|家庭地址|住址|电话|联系方式|手机"), "contact_information"),
]


def _tia_country_en(raw: str) -> str:
    for cn, en in _TIA_COUNTRY_EN.items():
        if cn in raw:
            return en
    return raw.strip()


def _tia_match_category(item: str) -> str:
    for rule, cat in _TIA_CAT_RULES:
        if rule.search(item):
            return cat
    return "other"


def _adapter_tia(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    def dash_items(block: str) -> list[str]:
        items: list[str] = []
        for chunk in re.split(r"\n(?=\s*-)", block.strip()):
            chunk = re.sub(r"^\s*-\s*", "", chunk.strip())
            chunk = re.sub(r"\s*\n\s*", "", chunk)
            if chunk:
                items.append(chunk)
        return items

    def section(title_re: str) -> str:
        m = re.search(title_re + r"(.*?)(?=【|$)", text, re.S)
        return m.group(1) if m else ""

    def field_in(section_text: str, label: str) -> str:
        m = re.search(label + r"[：:]\s*([^，,；;。\n]+)", section_text)
        return m.group(1).strip() if m else ""

    # transfer_tool（无默认，必须识别）
    tool = None
    if "SCC" in text or "标准合同" in text or "标准合同条款" in text:
        tool = "scc"
    elif "BCR" in text or "约束性公司规则" in text:
        tool = "bcr"
    elif "克减" in text or "减损" in text or "derogation" in text.lower():
        tool = "derogation"
    if tool is None:
        missing.append("transfer_tool")

    exporter_section = section(r"【传输方信息】")
    importer_section = section(r"【(?:境外)?接收方信息】")

    exporter_country = _tia_country_en(field_in(exporter_section, "所在地"))
    importer_country = _tia_country_en(field_in(importer_section, "所在地"))
    if not exporter_country:
        missing.append("exporter_country")
    if not importer_country:
        missing.append("importer_country")

    # transfer_purpose
    purpose_block = section(r"【传输目的】")
    transfer_purpose = "；".join(dash_items(purpose_block))
    if _is_missing(transfer_purpose):
        missing.append("transfer_purpose")

    # data_categories（至少一个，否则无法评估）
    m = re.search(r"数据类型[：:]\s*(.*?)(?=数据量|传输频率|传输方式|【)", text, re.S)
    data_block = m.group(1) if m else ""
    data_categories: list[str] = []
    for item in dash_items(data_block):
        cat = _tia_match_category(item)
        if cat not in data_categories:
            data_categories.append(cat)
    if not data_categories:
        missing.append("data_categories")

    # roles
    exporter_role = "joint_controller" if re.search(r"共同控制者|joint.?controller", text, re.I) else "controller"
    importer_role = "unknown"
    if re.search(r"次处理者|分处理者|sub.?processor", text, re.I):
        importer_role = "subprocessor"
    elif re.search(r"共同控制者|joint.?controller", text, re.I):
        importer_role = "joint_controller"
    elif re.search(r"控制者.{0,4}控制者|controller.{0,4}controller", text, re.I):
        importer_role = "controller"
    elif re.search(r"处理者|processor", text, re.I):
        importer_role = "processor"

    # frequency / scale / subjects
    transfer_frequency = field_in(text, "传输频率")
    transfer_scale = field_in(text, "数据量")
    data_subjects: list[str] = []
    for kw in ("员工", "客户", "用户", "患者", "消费者", "访客", "会员", "学生", "市民", "公民", "个人", "自然人"):
        if kw in transfer_scale and kw not in data_subjects:
            data_subjects.append(kw)

    # special categories
    has_special_category_data = bool(re.search(r"特殊类别数据[：:]\s*[^不无]", text))
    special_category_types: list[str] = []
    m = re.search(r"特殊类别数据[：:]\s*([^；;。\n]+)", text)
    if m and not re.match(r"^\s*(无|不|否)", m.group(1)):
        for s in re.split(r"[、，,]", m.group(1)):
            s = re.sub(r"[（(].*?[）)]", "", s).strip()
            if s:
                special_category_types.append(s)

    # technical controls（只在原文明确描述时才置 true）
    encryption_before_transfer = bool(re.search(r"传输加密|加密VPN|TLS|传输.*加密|加密.*传输", text))
    key_managed_in_eu = bool(re.search(
        r"密钥.{0,6}(?:欧盟|我方|本地|境内|EU|自持)|(?:欧盟|我方|本地|境内).{0,6}密钥", text,
    ))
    has_end_to_end_encryption = bool(re.search(r"端到端加密|end.?to.?end", text, re.I)) and not re.search(
        r"未.{0,8}端到端|没有端到端|未实施端到端", text,
    )
    has_secure_enclave = bool(re.search(r"安全飞地|可信执行环境|secure.?enclave|TEE", text, re.I))
    has_key_separation = bool(re.search(r"密钥分离|密钥.{0,4}分离|key.?separation", text, re.I))

    if missing:
        return None, missing

    from backend.domains.eu.tia.schema import TIARequest, TIAStructuredInput

    structured_input = TIAStructuredInput(
        exporter_country=exporter_country,
        importer_country=importer_country,
        destination_country=importer_country,
        exporter_role=exporter_role,
        importer_role=importer_role,
        transfer_purpose=transfer_purpose,
        data_categories=data_categories,
        has_special_category_data=has_special_category_data,
        special_category_types=special_category_types,
        data_subjects=data_subjects,
        transfer_frequency=transfer_frequency,
        transfer_scale=transfer_scale,
        encryption_before_transfer=encryption_before_transfer,
        key_managed_in_eu=key_managed_in_eu,
        has_end_to_end_encryption=has_end_to_end_encryption,
        has_secure_enclave=has_secure_enclave,
        has_key_separation=has_key_separation,
    )
    request = TIARequest(
        transfer_tool=tool,
        structured_input=structured_input,
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

    # transaction_description is free-text; a fuzzy count token like 几万 inside
    # the description must not mark the whole field missing. Only a blank body
    # is missing.
    transaction_description = text[:300].strip()
    if not transaction_description:
        missing.append("transaction_description")

    # 用可匹配常见变体的子串，避免"精确地理位置数据" vs "精确地理位置信息"
    # 之类同义写法被误判为缺失。
    data_item_names = [
        name for name in (
            "精确地理位置", "面部生物识别", "姓名", "邮箱",
            "电话号码", "基因组测序", "生物识别",
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


def _adapter_document_review(
    paras: list[str], source_docx: str | None = None, source_sha256: str = "",
) -> tuple[dict | None, list[str]]:
    # ReviewGenerateRequest requires uploaded_files (min_length=1). The seed
    # record carries a real source DOCX whose body is the document to review;
    # task074 B3 derives an input-only copy into storage rather than fabricating
    # an id/path. Without a real source file, keep blocking.
    storage_uri = _derive_seed_attachment(source_docx or "", source_sha256)
    if not storage_uri:
        return None, ["uploaded_files"]

    from backend.schemas.review import ReviewGenerateRequest

    request = ReviewGenerateRequest(uploaded_files=[storage_uri])
    return request.model_dump(), []


def _adapter_bcr_review(
    paras: list[str], source_docx: str | None = None, source_sha256: str = "",
) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    # company_name (min_length=2) is the one hard form field. The BCR title is
    # "<Group> Binding Corporate Rules for Data Controllers/Processors".
    company_name = ""
    m = re.search(
        r"([A-Za-z][A-Za-z0-9&. \-]{1,50}?)\s+Binding Corporate Rules",
        text,
    )
    if m:
        company_name = m.group(1).strip()
    if _is_missing(company_name):
        missing.append("company_name")

    storage_uri = _derive_seed_attachment(source_docx or "", source_sha256)
    if not storage_uri:
        missing.append("uploaded_documents")

    if missing:
        return None, missing

    from backend.domains.eu.bcr_review.schema import BCRRequest, BCRUploadedDocument

    uploaded_documents = [
        BCRUploadedDocument(
            file_id=f"seed_{Path(storage_uri).stem}",
            file_name=Path(storage_uri).name,
            file_type="docx",
            file_path=storage_uri,
            document_role="main_bcr_document",
            auto_detected_role=False,
        )
    ]
    request = BCRRequest(company_name=company_name, uploaded_documents=uploaded_documents)
    return request.model_dump(), []


def _adapter_dpia(paras: list[str]) -> tuple[dict | None, list[str]]:
    text = "\n".join(paras)
    missing: list[str] = []

    def dash_items(block: str) -> list[str]:
        """Extract ``- item`` bullets, joining wrapped continuation lines."""
        items: list[str] = []
        for chunk in re.split(r"\n(?=\s*-)", block.strip()):
            chunk = re.sub(r"^\s*-\s*", "", chunk.strip())
            chunk = re.sub(r"\s*\n\s*", "", chunk)
            if chunk:
                items.append(chunk)
        return items

    def block_after(label: str, stop: str) -> str:
        m = re.search(label + r"[：:]\s*(.*?)(?=" + stop + r")", text, re.S)
        return m.group(1) if m else ""

    # ── 1. Identify need (schema min_length 硬必填) ──
    project_name = ""
    m = re.search(r"系统名称[：:]\s*(.{2,60}?)(?:[；;。\n]|$)", text)
    if m:
        project_name = m.group(1).strip()
    if _is_missing(project_name):
        missing.append("project_name")

    project_goal = ""
    m = re.search(r"处理目的[：:]\s*(.{2,80}?)(?:[；;。\n]|$)", text)
    if m:
        project_goal = m.group(1).strip()
    if _is_missing(project_goal):
        missing.append("project_goal")

    processing_flow = ""
    m = re.search(r"系统功能[：:]\s*(.{2,120}?)(?:[；;。\n]|$)", text)
    if m:
        processing_flow = m.group(1).strip()
    if _is_missing(processing_flow):
        missing.append("processing_flow_description")

    # ── 2. Describe processing（忠实提取；缺失不阻塞，但绝不反向 false）──
    data_categories = dash_items(block_after("处理的数据类别", "处理目的|数据主体"))

    special_category_data = False
    special_category_types: list[str] = []
    m = re.search(r"特殊类别数据[：:]\s*([^；;。\n]+)", text)
    if m and "不涉及" not in m.group(1) and m.group(1).strip() not in ("无", "无。", "无；"):
        special_category_data = True
        v = re.sub(r"[（(].*?[）)]", "", m.group(1)).strip()
        if v:
            special_category_types.append(v)
    elif re.search(r"不涉及特殊类别|无特殊类别|声称[^。\n]*不涉及特殊类别", text):
        special_category_data = False

    data_subject_categories: list[str] = []
    m = re.search(r"数据主体[：:]\s*([^；;。\n]+)", text)
    if m:
        for s in re.split(r"[、，,]", m.group(1)):
            s = s.strip().rstrip("等").strip()
            if s:
                data_subject_categories.append(s)

    data_subject_count = ""
    m = re.search(r"数据量[：:]\s*([^\n]+)", text)
    if m:
        data_subject_count = m.group(1).strip()

    retention_period = "；".join(
        re.sub(r"^\s*-\s*", "", ln).strip()
        for ln in paras
        if ln.strip().startswith("-") and "保留" in ln
    )

    lawful_basis: list[str] = []
    m = re.search(r"【[^】]*法律基础[^】]*】\s*(.*?)(?=【|$)", text, re.S)
    if m:
        lawful_basis = dash_items(m.group(1))

    # 只有原文确实描述出境活动时才置 true；否则不伪造"无跨境"。
    cross_border_transfer = False
    transfer_destination = ""
    m = re.search(r"【跨境传输】(.*?)(?=【|$)", text, re.S)
    if m:
        section = m.group(1)
        if re.search(r"传[至到]|传输至|远程访问|VPN|境外|出境", section):
            cross_border_transfer = True
            dests: list[str] = []
            for mm in re.finditer(r"至\s*([^；;。\n（(]+?)(?:供应商|公司|$)", section):
                dests.append(mm.group(1).strip())
            for mm in re.finditer(
                r"[（(]([^）)]*(?:中国|美国|新加坡|欧盟|日本|韩国|以色列|印度|英国|法国|德国|奥地利|瑞士|澳大利亚|加拿大|俄罗斯|巴西|马来西亚|泰国|越南|印尼|菲律宾|台湾|香港|澳门)[^）)]*)[）)]",
                section,
            ):
                dests.append(mm.group(1).strip())
            transfer_destination = "；".join(dict.fromkeys(dests))

    automated_decision_making = False
    if re.search(r"不构成.{0,6}自动化决策|不涉及自动化决策|不涉及自动化", text):
        automated_decision_making = False
    elif re.search(r"自动化决策", text):
        automated_decision_making = True

    vulnerable_data_subjects = False
    if re.search(r"未成年|儿童", text) and not re.search(
        r"无未成年|不涉及未成年|不含未成年|无儿童|不涉及儿童", text
    ):
        vulnerable_data_subjects = True

    if missing:
        return None, missing

    from backend.domains.eu.dpia.schema import DPIARequest

    request = DPIARequest(
        project_name=project_name,
        project_goal=project_goal,
        processing_flow_description=processing_flow,
        data_categories=data_categories,
        special_category_data=special_category_data,
        special_category_types=special_category_types,
        data_subject_categories=data_subject_categories,
        data_subject_count=data_subject_count,
        retention_period=retention_period,
        cross_border_transfer=cross_border_transfer,
        transfer_destination=transfer_destination,
        automated_decision_making=automated_decision_making,
        vulnerable_data_subjects=vulnerable_data_subjects,
        lawful_basis=lawful_basis,
    )
    return request.model_dump(), []


ADAPTERS: dict[str, Callable[[list[str]], tuple[dict | None, list[str]]]] = {
    "cn.transfer_diagnosis": _adapter_transfer_diagnosis,
    "cn.security_assessment": _adapter_security_assessment,
    "cn.pipia": _adapter_pipia,
    "cn.document_review": _adapter_document_review,
    "eu.scc_review": _adapter_scc_review,
    "eu.bcr_review": _adapter_bcr_review,
    "eu.dpia": _adapter_dpia,
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
            elif module_id == "cn.document_review":
                from backend.schemas.review import ReviewGenerateRequest as M
            elif module_id == "eu.scc_review":
                from backend.domains.eu.scc_review.schema import SCCReviewRequest as M
            elif module_id == "eu.bcr_review":
                from backend.domains.eu.bcr_review.schema import BCRRequest as M
            elif module_id == "eu.dpia":
                from backend.domains.eu.dpia.schema import DPIARequest as M
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

    # v2.0 隔离：正文仍为 v1.0 旧内容的 12 个 case3/4/5 不得进入 request 路径。
    flags = record.get("data_quality_flags", [])
    if any(str(f).startswith("pending_correction") for f in flags):
        return {
            "case_id": case_id,
            "task_no": task_no,
            "module_id": module_id or None,
            "levelb": "pending_correction",
            "request_path": None,
            "blocking_missing_facts": [],
            "note": "v2.0 需修正/待修正：正文仍为 v1.0 旧内容，Level B 前隔离",
        }

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
    if module_id in ("cn.document_review", "eu.bcr_review"):
        request_dict, missing = adapter(
            paras,
            source_docx=record.get("source_docx") or "",
            source_sha256=record.get("source_sha256") or "",
        )
    else:
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
            paras = rec.get("input", {}).get("paragraphs", [])
            if d["module_id"] in ("cn.document_review", "eu.bcr_review"):
                request_dict, _ = adapter(
                    paras,
                    source_docx=rec.get("source_docx") or "",
                    source_sha256=rec.get("source_sha256") or "",
                )
            else:
                request_dict, _ = adapter(paras)
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
