from __future__ import annotations

import re


_CIIO_PATTERN = re.compile(r"(CIIO|关键信息基础设施|关基)", re.IGNORECASE)
_CIIO_NEG_PATTERN = re.compile(r"(非|不属于|未|不构成|未构成|不适用).{0,4}(CIIO|关键信息基础设施|关基)", re.IGNORECASE)
_IMPORTANT_PATTERN = re.compile(r"重要数据")
_IMPORTANT_NEG_PATTERN = re.compile(r"(不|未|不含|未涉及|未发现).{0,3}重要数据")

_COUNTRY_KEYWORDS = {
    "欧盟": ["欧盟", "EEA", "EU"],
    "美国": ["美国", "US", "USA"],
    "英国": ["英国", "UK"],
    "新加坡": ["新加坡", "Singapore"],
}


def check_cn_alignment(
    text: str,
    industry: str | None = None,
    is_ciio: bool | None = None,
    contains_important_data: bool | None = None,
    receiver_country: str | None = None,
) -> list[str]:
    if not text:
        return []

    issues: list[str] = []

    if is_ciio is False and _CIIO_PATTERN.search(text) and not _CIIO_NEG_PATTERN.search(text):
        issues.append("内容提及CIIO/关基，但输入is_ciio=False。")

    if contains_important_data is False and _IMPORTANT_PATTERN.search(text) and not _IMPORTANT_NEG_PATTERN.search(text):
        issues.append("内容提及重要数据，但输入contains_important_data=False。")

    if industry:
        if "电商" in text and "电商" not in industry:
            issues.append("内容出现“电商”相关表述，但输入行业非电商。")
        if "金融" in text and "金融" not in industry and "银行" not in industry:
            issues.append("内容出现“金融/银行”相关表述，但输入行业非金融。")

    if receiver_country:
        receiver_country_norm = receiver_country.lower()
        for label, tokens in _COUNTRY_KEYWORDS.items():
            if any(token.lower() in text.lower() for token in tokens):
                if not any(token.lower() in receiver_country_norm for token in tokens):
                    issues.append(f"内容出现“{label}”相关表述，但接收国家/地区为{receiver_country}。")

    return issues
