"""task082 标题策略、确定性语义、文本/禁词规则与 canonicalization。

规则采用稳定 ID（task080 的 S/M/T 命名），并登记 §6.4 的 TXT-*/SEM-* 别名。
语义等价（M1）默认只认 canonical / alias / candidate / purpose_code 职责标签的
确定性命中，不依赖一次不可重复的 LLM 判断。
"""

from __future__ import annotations

import re
from typing import Iterable

from backend.common.title_plan.models import PurposeCode

# ─────────────────────────────────────────────────────────────────────────────
# 规则 ID（task080 命名）与 §6.4 别名
# ─────────────────────────────────────────────────────────────────────────────

S1_UNKNOWN_SECTION = "S1"
S2_MISSING_REQUIRED = "S2"
S3_DUPLICATE_SECTION = "S3"
S4_REORDER = "S4"
S5_PARENT = "S5"
S6_LEVEL_ORDER = "S6"
S7_FIXED_RENAMED = "S7"
S8_DYNAMIC_PARENT = "S8"
S9_DYNAMIC_LIMIT = "S9"

M1_SEMANTIC_EQUIVALENCE = "M1"
M2_NO_FACT_ADDITION = "M2"
M3_NO_CONCLUSION = "M3"
M4_NO_STATUS_FLIP = "M4"
M5_NO_DUTY_MERGE = "M5"

T1_NONEMPTY = "T1"
T2_LENGTH = "T2"
T3_NO_MARKDOWN = "T3"
T4_NO_CITATION = "T4"
T5_NO_PROMPT_INSTRUCTION = "T5"
T6_NO_ORDINAL_PREFIX = "T6"
T7_NO_DUPLICATE = "T7"
T8_LOCALE = "T8"

# §6.4 文本/语义安全规则别名 → 主规则 ID
RULE_ALIASES: dict[str, str] = {
    "TXT-NONEMPTY": T1_NONEMPTY,
    "TXT-LENGTH": T2_LENGTH,
    "TXT-NO-NEWLINE": T3_NO_MARKDOWN,
    "TXT-NO-MARKDOWN": T3_NO_MARKDOWN,
    "TXT-NO-CITATION": T4_NO_CITATION,
    "TXT-NO-JSON": T5_NO_PROMPT_INSTRUCTION,
    "TXT-NO-PROMPT-INSTRUCTION": T5_NO_PROMPT_INSTRUCTION,
    "TXT-NO-ORDINAL-PREFIX": T6_NO_ORDINAL_PREFIX,
    "TXT-NO-DUPLICATE": T7_NO_DUPLICATE,
    "TXT-LOCALE": T8_LOCALE,
    "SEM-NO-UNVERIFIED-LEGAL-CONCLUSION": M3_NO_CONCLUSION,
    "SEM-NO-FACT-ADDITION": M2_NO_FACT_ADDITION,
    "SEM-NO-STATUS-FLIP": M4_NO_STATUS_FLIP,
    "SEM-NO-DUTY-MERGE": M5_NO_DUTY_MERGE,
}

STRUCTURAL_RULE_IDS = frozenset(
    {S1_UNKNOWN_SECTION, S2_MISSING_REQUIRED, S3_DUPLICATE_SECTION, S4_REORDER,
     S5_PARENT, S6_LEVEL_ORDER, S7_FIXED_RENAMED, S8_DYNAMIC_PARENT, S9_DYNAMIC_LIMIT}
)
SEMANTIC_RULE_IDS = frozenset(
    {M1_SEMANTIC_EQUIVALENCE, M2_NO_FACT_ADDITION, M3_NO_CONCLUSION,
     M4_NO_STATUS_FLIP, M5_NO_DUTY_MERGE}
)
TEXTUAL_RULE_IDS = frozenset(
    {T1_NONEMPTY, T2_LENGTH, T3_NO_MARKDOWN, T4_NO_CITATION,
     T5_NO_PROMPT_INSTRUCTION, T6_NO_ORDINAL_PREFIX, T7_NO_DUPLICATE, T8_LOCALE}
)

ALL_RULE_IDS = STRUCTURAL_RULE_IDS | SEMANTIC_RULE_IDS | TEXTUAL_RULE_IDS


# ─────────────────────────────────────────────────────────────────────────────
# 确定性标题 canonicalization
# ─────────────────────────────────────────────────────────────────────────────

_ORDINAL_PREFIX_RE = re.compile(
    r"^\s*(?:第\s*[一二三四五六七八九十百\d]+\s*[章节部分篇]|"
    r"[一二三四五六七八九十]+\s*[、．.]|"
    r"（[一二三四五六七八九十\d]+）|"
    r"\(\d+\)|"
    r"\d+\s*[、．.])\s*"
)
_MARKDOWN_RE = re.compile(r"[#*_>`~|]")
_PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


def strip_placeholders(text: str) -> str:
    """去除模板占位符（如 {company_name}）。占位符是程序注入 token，不参与
    markdown/locale 等文本安全检查。"""
    return _PLACEHOLDER_RE.sub("", text)
_WHITESPACE_RE = re.compile(r"\s+")
_CITATION_RE = re.compile(r"\{\{\s*CIT-[^}]*\}\}|\[CITATION\]|\[[A-Za-z-]+\s+\d+\]", re.IGNORECASE)
_JSON_FRAGMENT_RE = re.compile(r'[\{\[][^\n]*["\']\s*:\s*["\']')
_PROMPT_INSTRUCTION_RE = re.compile(
    r"忽略|无视|改写系统提示|输出\s*JSON|作为\s*AI|系统提示|prompt|"
    r"不要遵循|忘记之前|developer\s*message",
    re.IGNORECASE,
)


def normalize_title(text: str, *, strip_ordinal: bool = False) -> str:
    """规范化标题文本，返回可比较的核心字符串。

    - 统一换行为空格；
    - 去除 Markdown 标记；
    - 折叠空白；
    - ``strip_ordinal=True`` 时剥离中文/数字序号前缀（用于职责标签命中）。
    """
    if not text:
        return ""
    out = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    out = _MARKDOWN_RE.sub("", out)
    if strip_ordinal:
        out = _ORDINAL_PREFIX_RE.sub("", out)
    out = _WHITESPACE_RE.sub(" ", out)
    return out.strip()


# ─────────────────────────────────────────────────────────────────────────────
# purpose_code 职责标签与确定性派生
# ─────────────────────────────────────────────────────────────────────────────

PURPOSE_LABELS: dict[PurposeCode, tuple[str, ...]] = {
    PurposeCode.DOCUMENT_TITLE: ("报告", "草案", "审查报告", "评估报告"),
    PurposeCode.EXECUTIVE_SUMMARY: ("摘要", "概要"),
    PurposeCode.OVERVIEW: ("概述", "概况", "整体情况", "工作情况"),
    PurposeCode.SCOPE: ("范围", "适用性", "适用"),
    PurposeCode.BASIC_INFO: ("基本情况", "基本信息", "基础信息", "企业"),
    PurposeCode.DATA_SCOPE: ("数据类型", "数据情况", "数据规模", "数据分类", "字段", "敏感信息"),
    PurposeCode.PROCESSING_DESCRIPTION: ("处理活动", "处理者", "处理流程", "描述处理"),
    PurposeCode.TRANSFER_ACTIVITY: ("出境活动", "跨境传输", "传输场景"),
    PurposeCode.LEGAL_BASIS: ("合法性", "必要性", "法律基础", "法律文件", "责任义务"),
    PurposeCode.CONSULTATION: ("咨询",),
    PurposeCode.NECESSITY_PROPORTIONALITY: ("必要性", "相称性", "识别需求", "必要性预判"),
    PurposeCode.RECIPIENT: ("接收方",),
    PurposeCode.RIGHTS_IMPACT: ("权益", "权利", "消费者权利", "权益影响"),
    PurposeCode.SECURITY_MEASURES: ("安全措施", "保障能力", "技术措施", "传输机制", "安全"),
    PurposeCode.RISK_ASSESSMENT: ("风险识别", "风险详情", "风险匹配", "风险提示", "风险自评估"),
    PurposeCode.RISK_DETAILS: ("风险",),
    PurposeCode.RISK_REMEDIATION: ("剩余风险", "整改"),
    PurposeCode.MITIGATION: ("降低风险", "缓解", "降低"),
    PurposeCode.FINDINGS: ("逐条问题", "条款级", "发现", "问题", "finding"),
    PurposeCode.CONCLUSION: ("结论", "评级", "可行性"),
    PurposeCode.COMPLIANCE_ACTIONS: ("合规措施", "合规建议"),
    PurposeCode.ACTIONS: ("行动清单", "路线图", "后续行动", "优先级", "行动"),
    PurposeCode.RECOMMENDATIONS: ("建议", "修改建议"),
    PurposeCode.CITATIONS: ("法规", "引用", "条文", "依据"),
    PurposeCode.BOUNDARY: ("边界", "置信度", "系统生成", "其他情况", "免责"),
    PurposeCode.GAP: ("缺口", "待补充"),
    PurposeCode.PATH: ("判定", "路径"),
    PurposeCode.MONITORING: ("监控", "复审", "持续"),
    PurposeCode.SIGNOFF: ("签署", "记录"),
    PurposeCode.APPENDIX: ("附录", "附件"),
}

_DERIVE_RULES: tuple[tuple[tuple[str, ...], PurposeCode], ...] = (
    (("{company_name}", "{project_name}", "{document_title}", "{exporter_profile}"), PurposeCode.DOCUMENT_TITLE),
    (("摘要",), PurposeCode.EXECUTIVE_SUMMARY),
    (("识别需求", "必要性预判"), PurposeCode.NECESSITY_PROPORTIONALITY),
    (("咨询",), PurposeCode.CONSULTATION),
    (("签署", "记录"), PurposeCode.SIGNOFF),
    (("降低风险", "缓解"), PurposeCode.MITIGATION),
    (("风险识别", "风险详情", "风险匹配", "风险提示", "风险自评估"), PurposeCode.RISK_ASSESSMENT),
    (("剩余风险", "整改"), PurposeCode.RISK_REMEDIATION),
    (("结论", "评级", "可行性"), PurposeCode.CONCLUSION),
    (("数据类型", "数据情况", "数据规模", "数据分类", "敏感信息", "拟出境数据"), PurposeCode.DATA_SCOPE),
    (("合法性", "法律基础", "法律文件", "责任义务", "必要性", "相称性"), PurposeCode.LEGAL_BASIS),
    (("接收方",), PurposeCode.RECIPIENT),
    (("权益", "权利", "消费者权利"), PurposeCode.RIGHTS_IMPACT),
    (("安全措施", "保障能力", "技术措施", "传输机制", "安全"), PurposeCode.SECURITY_MEASURES),
    (("处理活动", "处理者", "描述处理", "处理流程"), PurposeCode.PROCESSING_DESCRIPTION),
    (("出境活动", "跨境传输", "传输场景", "传输工具"), PurposeCode.TRANSFER_ACTIVITY),
    (("基本情况", "基本信息", "基础信息", "企业"), PurposeCode.BASIC_INFO),
    (("范围", "适用性", "类型与"), PurposeCode.SCOPE),
    (("逐条问题", "条款级", "发现", "finding", "问题"), PurposeCode.FINDINGS),
    (("法规", "引用", "条文", "依据"), PurposeCode.CITATIONS),
    (("合规措施", "合规建议"), PurposeCode.COMPLIANCE_ACTIONS),
    (("行动清单", "路线图", "后续行动", "优先级", "行动"), PurposeCode.ACTIONS),
    (("建议",), PurposeCode.RECOMMENDATIONS),
    (("边界", "置信度", "系统生成", "其他情况", "免责"), PurposeCode.BOUNDARY),
    (("缺口", "待补充"), PurposeCode.GAP),
    (("判定", "路径"), PurposeCode.PATH),
    (("监控", "复审", "持续"), PurposeCode.MONITORING),
    (("附录", "附件"), PurposeCode.APPENDIX),
    (("整体", "概况", "概要", "文件概要", "概述"), PurposeCode.OVERVIEW),
    (("风险",), PurposeCode.RISK_DETAILS),
)


def derive_purpose_code(canonical_title: str, semantic_purpose: str = "") -> PurposeCode:
    """从 canonical_title 确定性派生 purpose_code（闭集职责代码）。

    不依赖模型自由解释；按固定优先级匹配关键词，保证可复现。
    """
    title = canonical_title or ""
    for keywords, code in _DERIVE_RULES:
        if any(k in title for k in keywords):
            return code
    # 兜底：语义文本中有明显职责词时再尝试一次，否则 OVERVIEW
    for keywords, code in _DERIVE_RULES:
        if any(k in (semantic_purpose or "") for k in keywords):
            return code
    return PurposeCode.OVERVIEW


def purpose_labels(code: PurposeCode | None) -> tuple[str, ...]:
    if code is None:
        return ()
    return PURPOSE_LABELS.get(code, ())


def title_hits_purpose(display_title: str, code: PurposeCode | None) -> bool:
    """display_title 经确定性 normalizer 后是否命中职责标签。"""
    normalized = normalize_title(display_title, strip_ordinal=True)
    if not normalized:
        return False
    return any(label in normalized for label in purpose_labels(code))


# ─────────────────────────────────────────────────────────────────────────────
# 禁止词 / 注入 / 事实 / 结论 模式
# ─────────────────────────────────────────────────────────────────────────────

CONCLUSION_PATTERNS = (
    re.compile(r"合规|合法|无风险|确定违法|已合规|不违法|符合要求"),
)
STATUS_FLIP_PATTERNS = (
    re.compile(r"已完成|已满足|已获得同意|已整改|已通过|已解决"),
)
FACT_ADDITION_PATTERNS = (
    re.compile(r"\d+\s*(?:人|名|国|个国家|家|项|条|万|亿|年|月|日|个)"),
    re.compile(r"第\s*\d+\s*条"),
    re.compile(r"Art\.?\s*\d+", re.IGNORECASE),
    re.compile(r"\b(?:GDPR|CCPA|CPRA|EO\s*14117|PIPL)\b", re.IGNORECASE),
)
ORDINAL_PREFIX_HEAD_RE = re.compile(
    r"^(?:第\s*[一二三四五六七八九十百\d]+\s*[章节部分篇]|"
    r"[一二三四五六七八九十]+\s*[、．.]|"
    r"（[一二三四五六七八九十\d]+）|"
    r"\(\d+\)|"
    r"\d+\s*[、．.])"
)
_LOCALE_ALLOWED_RE = re.compile(r"^[一-鿿A-Za-z0-9\s·—\-—（）()（）&：:，,。\.%％/{}\[\]<>]+$")


def matches_any(text: str, patterns: Iterable[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)


__all__ = [
    "ALL_RULE_IDS",
    "CONCLUSION_PATTERNS",
    "FACT_ADDITION_PATTERNS",
    "M1_SEMANTIC_EQUIVALENCE",
    "M2_NO_FACT_ADDITION",
    "M3_NO_CONCLUSION",
    "M4_NO_STATUS_FLIP",
    "M5_NO_DUTY_MERGE",
    "ORDINAL_PREFIX_HEAD_RE",
    "RULE_ALIASES",
    "S1_UNKNOWN_SECTION",
    "S2_MISSING_REQUIRED",
    "S3_DUPLICATE_SECTION",
    "S4_REORDER",
    "S5_PARENT",
    "S6_LEVEL_ORDER",
    "S7_FIXED_RENAMED",
    "S8_DYNAMIC_PARENT",
    "S9_DYNAMIC_LIMIT",
    "SEMANTIC_RULE_IDS",
    "STATUS_FLIP_PATTERNS",
    "STRUCTURAL_RULE_IDS",
    "T1_NONEMPTY",
    "T2_LENGTH",
    "T3_NO_MARKDOWN",
    "T4_NO_CITATION",
    "T5_NO_PROMPT_INSTRUCTION",
    "T6_NO_ORDINAL_PREFIX",
    "T7_NO_DUPLICATE",
    "T8_LOCALE",
    "TEXTUAL_RULE_IDS",
    "_CITATION_RE",
    "_JSON_FRAGMENT_RE",
    "_LOCALE_ALLOWED_RE",
    "_PROMPT_INSTRUCTION_RE",
    "derive_purpose_code",
    "matches_any",
    "normalize_title",
    "purpose_labels",
    "strip_placeholders",
    "title_hits_purpose",
]
