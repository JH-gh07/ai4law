#!/usr/bin/env python3
"""
ingest_regional_laws.py — P2 regional law ingestion

Adds sources.csv rows + regulation_articles.jsonl entries for all regional laws
under resources/new/知识库补充/.

Usage:
    python3 scripts/ingest_regional_laws.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).parent.parent
SOURCES_CSV = ROOT / "resources/legal/catalog/sources.csv"
ARTICLES_JSONL = ROOT / "resources/legal/registry/regulation_articles.jsonl"
PDF_BASE = ROOT / "resources/new/知识库补充"

# ---------------------------------------------------------------------------
# Kanji numeral converter (for Japanese laws)
# ---------------------------------------------------------------------------
_KANJI = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9,
          "十": 10, "百": 100, "千": 1000, "万": 10000}


def kanji_to_int(s: str) -> int:
    s = s.strip()
    if s.isdigit():
        return int(s)
    result = 0
    current = 0
    for c in s:
        v = _KANJI.get(c)
        if v is None:
            continue
        if v >= 10:
            result += (current or 1) * v
            current = 0
        else:
            current = v
    return result + current


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------
def extract_pdf_text(pdf_path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout
    except Exception as e:
        print(f"  [WARN] pdftotext failed for {pdf_path.name}: {e}", file=sys.stderr)
        return ""


# ---------------------------------------------------------------------------
# Article parsers  — each returns list of (article_no_str, full_text)
# ---------------------------------------------------------------------------

def parse_chinese_articles(text: str, char: str = "条") -> list[tuple[str, str]]:
    """Parse '第N条' or '第 N 條' style articles (CN/TW/HK/MO)."""
    # Handles: 第1条 / 第 1 條 / 第一条 / 第十三条
    pattern = re.compile(
        r"第\s*([0-9一二三四五六七八九十百千]+(?:之[0-9一二三四五六七八九十百千]+)?)\s*[条條]"
    )
    # Split by article header positions
    segments: list[tuple[str, str]] = []
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        art_raw = m.group(1).replace(" ", "")
        # Normalise to Arabic
        if re.fullmatch(r"[0-9]+(?:之[0-9]+)?", art_raw):
            art_no = art_raw
        else:
            # Contains kanji — convert
            if "之" in art_raw:
                base, sub = art_raw.split("之", 1)
                art_no = f"{kanji_to_int(base)}之{kanji_to_int(sub)}"
            else:
                art_no = str(kanji_to_int(art_raw))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.start():end].strip()
        if art_no and content:
            segments.append((art_no, content))
    return segments


def parse_japanese_articles(text: str) -> list[tuple[str, str]]:
    """Parse Japanese '第X条' articles (kanji numerals)."""
    pattern = re.compile(
        r"第([一二三四五六七八九十百千\d]+(?:の[一二三四五六七八九十百千\d]+)?)条"
    )
    segments: list[tuple[str, str]] = []
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        raw = m.group(1)
        if "の" in raw:
            base, sub = raw.split("の", 1)
            art_no = f"{kanji_to_int(base)}之{kanji_to_int(sub)}"
        else:
            art_no = str(kanji_to_int(raw))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.start():end].strip()
        if art_no and content:
            segments.append((art_no, content))
    return segments


def parse_korean_articles(text: str) -> list[tuple[str, str]]:
    """Parse Korean '제N조' articles."""
    pattern = re.compile(r"제(\d+)조[（(（]")
    segments: list[tuple[str, str]] = []
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        art_no = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.start():end].strip()
        if art_no and content:
            segments.append((art_no, content))
    return segments


def parse_english_sections(text: str) -> list[tuple[str, str]]:
    """Parse 'N.' section-numbered English laws (Singapore, Malaysia)."""
    # Match lines that start with a standalone number + period
    pattern = re.compile(r"(?m)^(\d+)\.\s+\S")
    segments: list[tuple[str, str]] = []
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        art_no = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.start():end].strip()
        if art_no and content:
            segments.append((art_no, content))
    return segments


def parse_malay_sections(text: str) -> list[tuple[str, str]]:
    """Parse Malay 'Seksyen N' laws (Malaysia)."""
    pattern = re.compile(r"(?m)^Seksyen\s+(\d+)\b")
    segments: list[tuple[str, str]] = []
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        art_no = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.start():end].strip()
        if art_no and content:
            segments.append((art_no, content))
    return segments


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------
@dataclass
class SourceDef:
    source_id: str
    jurisdiction: str
    path: str
    doc_type: str
    title: str
    source_org: str
    authority_level: str
    publish_date: str
    effective_date: str
    status: str
    url: str
    usage_priority: str
    notes: str
    module: str
    category: str
    usage: str
    binding_force: str
    authority: str
    publisher: str
    suitable_for: str
    report_usage: str
    summary: str
    knowledge_url: str
    law_name_for_articles: str          # display name used in article entries
    pdf_subpath: str                     # relative to PDF_BASE
    parser: Callable[[str], list[tuple[str, str]]]
    layer: str = "legal_rules"
    snapshot_path: str = ""
    origin_path: str = ""
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Source definitions  (51 sources across 8 jurisdictions)
# ---------------------------------------------------------------------------
PDF_VN = "越南"
PDF_SG = "新加坡"
PDF_JP = "日韩/日本"
PDF_KR = "日韩/韩国"
PDF_HK = "港澳台/香港"
PDF_MO = "港澳台/澳门"
PDF_TW = "港澳台/台湾"
PDF_MY = "马来西亚"

SOURCES: list[SourceDef] = [
    # ── Vietnam ──────────────────────────────────────────────────────────────
    SourceDef(
        source_id="VN-LAW-001", jurisdiction="vn", path="all",
        doc_type="law",
        title="越南个人数据保护法 2025（第91/2025/QH15号）",
        law_name_for_articles="越南个人数据保护法（91/2025）",
        source_org="越南国会", authority_level="official",
        publish_date="2025-06-27", effective_date="2026-01-01", status="effective",
        url="https://chinhphu.vn/",
        usage_priority="P1", notes="越南核心个人数据保护基本法",
        module="intl-vn", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="越南国会",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="越南2025年个人数据保护法，建立个人数据处理基本框架，含跨境传输规则。",
        knowledge_url="/knowledge/sources/VN-LAW-001",
        pdf_subpath=f"{PDF_VN}/A01_Law on Personal Data Protection 2025_个人数据保护法_91-2025-QH15.pdf",
        parser=lambda t: [],  # image-based PDF, no extractable text
    ),
    SourceDef(
        source_id="VN-REG-002", jurisdiction="vn", path="all",
        doc_type="administrative_regulation",
        title="越南个人数据保护法实施法令（第356/2025/NĐ-CP号）",
        law_name_for_articles="越南个人数据保护法实施法令（356/2025）",
        source_org="越南政府", authority_level="official",
        publish_date="2025-12-25", effective_date="2026-01-01", status="effective",
        url="https://chinhphu.vn/",
        usage_priority="P1", notes="VN-LAW-001 实施法令",
        module="intl-vn", category="行政法规", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="越南政府",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="越南个人数据保护法实施法令，细化数据处理者义务、认证制度和跨境传输许可流程。",
        knowledge_url="/knowledge/sources/VN-REG-002",
        pdf_subpath=f"{PDF_VN}/A02_Decree No. 356-2025-ND-CP_个人数据保护法实施法令.pdf",
        parser=lambda t: [],
    ),
    SourceDef(
        source_id="VN-LAW-003", jurisdiction="vn", path="all",
        doc_type="law",
        title="越南数据法 2024（第60/2024/QH15号）",
        law_name_for_articles="越南数据法（60/2024）",
        source_org="越南国会", authority_level="official",
        publish_date="2024-06-29", effective_date="2025-01-01", status="effective",
        url="https://chinhphu.vn/",
        usage_priority="P1", notes="越南数据治理基本法",
        module="intl-vn", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="越南国会",
        suitable_for="路径判断、数据分类", report_usage="可直接引用条文号",
        summary="越南数据法，建立数据治理基本框架，含重要数据和核心数据分类制度。",
        knowledge_url="/knowledge/sources/VN-LAW-003",
        pdf_subpath=f"{PDF_VN}/A03_Law on Data 2024_数据法_60-2024-QH15.pdf",
        parser=lambda t: [],
    ),
    SourceDef(
        source_id="VN-REG-004", jurisdiction="vn", path="all",
        doc_type="administrative_regulation",
        title="越南数据法实施法令（第165/2025/NĐ-CP号）",
        law_name_for_articles="越南数据法实施法令（165/2025）",
        source_org="越南政府", authority_level="official",
        publish_date="2025-06-15", effective_date="2025-07-01", status="effective",
        url="https://chinhphu.vn/",
        usage_priority="P1", notes="VN-LAW-003 实施法令",
        module="intl-vn", category="行政法规", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="越南政府",
        suitable_for="数据分类、跨境处理", report_usage="可直接引用条文号",
        summary="越南数据法实施法令，细化重要数据、核心数据认定标准及跨境处理许可程序。",
        knowledge_url="/knowledge/sources/VN-REG-004",
        pdf_subpath=f"{PDF_VN}/A04_Decree No. 165-2025-ND-CP_数据法实施法令.pdf",
        parser=lambda t: [],
    ),
    SourceDef(
        source_id="VN-REG-005", jurisdiction="vn", path="all",
        doc_type="administrative_regulation",
        title="越南重要数据和核心数据目录（第20/2025/QĐ-TTg号）",
        law_name_for_articles="越南重要数据和核心数据目录（20/2025）",
        source_org="越南政府总理", authority_level="official",
        publish_date="2025-06-15", effective_date="2025-07-01", status="effective",
        url="https://chinhphu.vn/",
        usage_priority="P2", notes="越南核心数据分类目录",
        module="intl-vn", category="行政法规", usage="数据分类参考",
        binding_force="mandatory", authority="medium", publisher="越南政府总理",
        suitable_for="数据分类判断", report_usage="参考引用",
        summary="越南政府发布的重要数据和核心数据分类目录，用于确定哪些数据受跨境传输严格限制。",
        knowledge_url="/knowledge/sources/VN-REG-005",
        pdf_subpath=f"{PDF_VN}/A05_Decision No. 20-2025-QD-TTg_重要数据和核心数据目录.pdf",
        parser=lambda t: [],
    ),
    SourceDef(
        source_id="VN-LAW-006", jurisdiction="vn", path="all",
        doc_type="law",
        title="越南网络安全法 2025（第116/2025/QH15号）",
        law_name_for_articles="越南网络安全法（116/2025）",
        source_org="越南国会", authority_level="official",
        publish_date="2025-11-29", effective_date="2026-07-01", status="effective",
        url="https://chinhphu.vn/",
        usage_priority="P1", notes="越南网络安全基本法",
        module="intl-vn", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="越南国会",
        suitable_for="路径判断、网络安全合规", report_usage="可直接引用条文号",
        summary="越南新版网络安全法，含关键信息基础设施保护、数据本地化及跨境传输规定。",
        knowledge_url="/knowledge/sources/VN-LAW-006",
        pdf_subpath=f"{PDF_VN}/B01_Law on Cybersecurity 2025_网络安全法_116-2025-QH15.pdf",
        parser=lambda t: [],
    ),

    # ── Singapore ─────────────────────────────────────────────────────────────
    SourceDef(
        source_id="SG-LAW-001", jurisdiction="sg", path="all",
        doc_type="law",
        title="新加坡个人数据保护法 2012（2025-12-05起适用版）",
        law_name_for_articles="新加坡个人数据保护法（PDPA 2012）",
        source_org="新加坡法律修订委员会", authority_level="official",
        publish_date="2012-11-20", effective_date="2025-12-05", status="effective",
        url="https://sso.agc.gov.sg/Act/PDPA2012",
        usage_priority="P1", notes="新加坡个人数据保护基本法",
        module="intl-sg", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="新加坡国会",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="新加坡PDPA，规定个人数据收集、使用、披露和保护的基本义务，含数据泄露通知和跨境传输规则。",
        knowledge_url="/knowledge/sources/SG-LAW-001",
        pdf_subpath=f"{PDF_SG}/A01_Personal Data Protection Act 2012_个人数据保护法_现行整合文本_2025-12-05起适用.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="SG-REG-002", jurisdiction="sg", path="all",
        doc_type="administrative_regulation",
        title="新加坡个人数据保护条例 2021",
        law_name_for_articles="新加坡个人数据保护条例（PDPR 2021）",
        source_org="新加坡个人数据保护委员会", authority_level="official",
        publish_date="2021-02-01", effective_date="2021-02-01", status="effective",
        url="https://sso.agc.gov.sg/SL/PDPA2012-S64-2021",
        usage_priority="P1", notes="PDPA配套条例，含跨境传输规则",
        module="intl-sg", category="行政法规", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="新加坡个人数据保护委员会",
        suitable_for="跨境传输合规", report_usage="可直接引用条文号",
        summary="新加坡PDPR 2021，细化PDPA跨境传输保障规则，规定合同条款、认证和约束性企业规则等机制。",
        knowledge_url="/knowledge/sources/SG-REG-002",
        pdf_subpath=f"{PDF_SG}/A02_Personal Data Protection Regulations 2021_个人数据保护条例_含跨境传输规则_现行整合文本.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="SG-REG-003", jurisdiction="sg", path="all",
        doc_type="administrative_regulation",
        title="新加坡数据泄露通知条例 2021",
        law_name_for_articles="新加坡数据泄露通知条例 2021",
        source_org="新加坡个人数据保护委员会", authority_level="official",
        publish_date="2021-02-01", effective_date="2021-02-01", status="effective",
        url="https://sso.agc.gov.sg/SL/PDPA2012-S63-2021",
        usage_priority="P2", notes="数据泄露通知机制配套条例",
        module="intl-sg", category="行政法规", usage="合规操作参考",
        binding_force="mandatory", authority="high", publisher="新加坡个人数据保护委员会",
        suitable_for="数据泄露应急响应", report_usage="可直接引用条文号",
        summary="规定新加坡数据泄露强制通知的触发条件、时限和通知内容要求。",
        knowledge_url="/knowledge/sources/SG-REG-003",
        pdf_subpath=f"{PDF_SG}/A03_Personal Data Protection (Notification of Data Breaches) Regulations 2021_数据泄露通知条例_现行整合文本.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="SG-REG-004", jurisdiction="sg", path="all",
        doc_type="administrative_regulation",
        title="新加坡个人数据保护（执法）条例 2021",
        law_name_for_articles="新加坡个人数据保护执法条例 2021",
        source_org="新加坡个人数据保护委员会", authority_level="official",
        publish_date="2021-02-01", effective_date="2021-02-01", status="effective",
        url="https://sso.agc.gov.sg/SL/PDPA2012-S62-2021",
        usage_priority="P2", notes="行政处罚程序配套条例",
        module="intl-sg", category="行政法规", usage="合规操作参考",
        binding_force="mandatory", authority="high", publisher="新加坡个人数据保护委员会",
        suitable_for="行政执法程序", report_usage="可直接引用条文号",
        summary="规定新加坡PDPC对违反PDPA行为的行政执法调查程序和处罚规则。",
        knowledge_url="/knowledge/sources/SG-REG-004",
        pdf_subpath=f"{PDF_SG}/A04_Personal Data Protection (Enforcement) Regulations 2021_执法条例_现行整合文本.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="SG-LAW-005", jurisdiction="sg", path="all",
        doc_type="law",
        title="新加坡网络安全法 2018",
        law_name_for_articles="新加坡网络安全法（Cybersecurity Act 2018）",
        source_org="新加坡网络安全局", authority_level="official",
        publish_date="2018-02-05", effective_date="2018-08-31", status="effective",
        url="https://sso.agc.gov.sg/Act/CSA2018",
        usage_priority="P1", notes="新加坡关键信息基础设施保护基本法",
        module="intl-sg", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="新加坡国会",
        suitable_for="关键基础设施合规判断", report_usage="可直接引用条文号",
        summary="新加坡网络安全法，规定关键信息基础设施（CII）保护义务和网络安全事件报告要求。",
        knowledge_url="/knowledge/sources/SG-LAW-005",
        pdf_subpath=f"{PDF_SG}/B01_Cybersecurity Act 2018_网络安全法_现行整合文本.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="SG-REG-006", jurisdiction="sg", path="all",
        doc_type="administrative_regulation",
        title="新加坡第三方所有关键信息基础设施网络安全条例 2026",
        law_name_for_articles="新加坡第三方CII网络安全条例 2026",
        source_org="新加坡网络安全局", authority_level="official",
        publish_date="2026-01-01", effective_date="2026-01-01", status="effective",
        url="https://sso.agc.gov.sg/",
        usage_priority="P2", notes="新加坡Cybersecurity Act第三方CII配套条例",
        module="intl-sg", category="行政法规", usage="合规操作参考",
        binding_force="mandatory", authority="high", publisher="新加坡网络安全局",
        suitable_for="CII关键基础设施合规", report_usage="可直接引用条文号",
        summary="规定第三方拥有但属于关键信息基础设施的网络安全责任分配和合规义务。",
        knowledge_url="/knowledge/sources/SG-REG-006",
        pdf_subpath=f"{PDF_SG}/B02_Cybersecurity (Providers of Essential Service Responsible for Cybersecurity of Third-Party-Owned Critical Information Infrastructure) Regulations 2026_第三方所有关键信息基础设施条例.pdf",
        parser=parse_english_sections,
    ),
]

_JP_SOURCES: list[SourceDef] = [
    # ── Japan ─────────────────────────────────────────────────────────────────
    SourceDef(
        source_id="JP-LAW-001", jurisdiction="jp", path="all",
        doc_type="law",
        title="日本个人信息保护法（令和3年改正版）",
        law_name_for_articles="日本个人信息保护法（令和3年）",
        source_org="日本个人信息保护委员会", authority_level="official",
        publish_date="2021-05-12", effective_date="2022-04-01", status="effective",
        url="https://www.ppc.go.jp/personalinfo/legal/",
        usage_priority="P1", notes="日本核心个人信息保护法",
        module="intl-jp", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="日本国会",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="日本2021年修订版个人信息保护法，统一公私部门数据保护规则，强化跨境传输和假名化处理制度。",
        knowledge_url="/knowledge/sources/JP-LAW-001",
        pdf_subpath="日韩/日本/A01_个人情報の保護に関する法律_个人信息保护法_令和3年改正版.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-REG-002", jurisdiction="jp", path="all",
        doc_type="administrative_regulation",
        title="日本个人信息保护委员会规则（第3号）",
        law_name_for_articles="日本个人信息保护委员会规则（第3号）",
        source_org="日本个人信息保护委员会", authority_level="official",
        publish_date="2021-08-02", effective_date="2022-04-01", status="effective",
        url="https://www.ppc.go.jp/personalinfo/legal/",
        usage_priority="P1", notes="个人信息保护法实施细则",
        module="intl-jp", category="行政法规", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="日本个人信息保护委员会",
        suitable_for="路径判断、合规操作", report_usage="可直接引用条文号",
        summary="日本个人信息保护委员会规则第3号，规定个人信息处理的具体操作规范和报告程序。",
        knowledge_url="/knowledge/sources/JP-REG-002",
        pdf_subpath="日韩/日本/A02_個人情報の保護に関する法律施行規則（個人情報保護委員会規則第3号）.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-REG-003", jurisdiction="jp", path="all",
        doc_type="administrative_regulation",
        title="日本个人信息保护法实施令（2021年政令第311号）",
        law_name_for_articles="日本个人信息保护法实施令（政令311号）",
        source_org="日本内阁", authority_level="official",
        publish_date="2021-08-18", effective_date="2022-04-01", status="effective",
        url="https://www.ppc.go.jp/personalinfo/legal/",
        usage_priority="P1", notes="个人信息保护法政令",
        module="intl-jp", category="行政法规", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="日本内阁",
        suitable_for="合规操作", report_usage="可直接引用条文号",
        summary="日本个人信息保护法实施令，规定义务免除门槛和特殊处理条件。",
        knowledge_url="/knowledge/sources/JP-REG-003",
        pdf_subpath="日韩/日本/A03_個人情報の保護に関する法律施行令（令和三年政令第311号）.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-GUIDE-004", jurisdiction="jp", path="all",
        doc_type="guideline",
        title="日本个人信息保护法通则指南（2022年修订）",
        law_name_for_articles="日本个人信息保护通则指南（2022）",
        source_org="日本个人信息保护委员会", authority_level="guidance",
        publish_date="2022-04-01", effective_date="2022-04-01", status="effective",
        url="https://www.ppc.go.jp/personalinfo/legal/",
        usage_priority="P2", notes="日本PPC权威解释指南",
        module="intl-jp", category="指导文件", usage="解释参考",
        binding_force="recommended", authority="medium", publisher="日本个人信息保护委员会",
        suitable_for="条文解释、合规建议", report_usage="参考引用",
        summary="日本个人信息保护委员会发布的通则解释指南，提供条文权威解读和FAQ。",
        knowledge_url="/knowledge/sources/JP-GUIDE-004",
        pdf_subpath="日韩/日本/A04_個人情報の保護に関する法律についてのガイドライン（通則編）.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-GUIDE-005", jurisdiction="jp", path="all",
        doc_type="guideline",
        title="日本个人信息保护法境外提供指南（2022年修订）",
        law_name_for_articles="日本个人信息保护境外提供指南（2022）",
        source_org="日本个人信息保护委员会", authority_level="guidance",
        publish_date="2022-04-01", effective_date="2022-04-01", status="effective",
        url="https://www.ppc.go.jp/personalinfo/legal/",
        usage_priority="P1", notes="日本跨境传输专项指南",
        module="intl-jp", category="指导文件", usage="跨境传输审查参考",
        binding_force="recommended", authority="medium", publisher="日本个人信息保护委员会",
        suitable_for="跨境传输合规判断", report_usage="参考引用",
        summary="专门针对个人信息境外第三方提供的权威解读，含充分性认定国家列表和标准合同条款说明。",
        knowledge_url="/knowledge/sources/JP-GUIDE-005",
        pdf_subpath="日韩/日本/A05_個人情報の保護に関する法律についてのガイドライン（外国にある第三者への提供編）.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-GUIDE-006", jurisdiction="jp", path="all",
        doc_type="guideline",
        title="日本个人信息保护法第三方提供记录指南（2022年修订）",
        law_name_for_articles="日本个人信息保护第三方提供记录指南（2022）",
        source_org="日本个人信息保护委员会", authority_level="guidance",
        publish_date="2022-04-01", effective_date="2022-04-01", status="effective",
        url="https://www.ppc.go.jp/personalinfo/legal/",
        usage_priority="P2", notes="第三方提供记录义务指南",
        module="intl-jp", category="指导文件", usage="合规操作参考",
        binding_force="recommended", authority="medium", publisher="日本个人信息保护委员会",
        suitable_for="记录留存义务合规", report_usage="参考引用",
        summary="规定向第三方提供个人信息时的记录义务内容格式和保存要求。",
        knowledge_url="/knowledge/sources/JP-GUIDE-006",
        pdf_subpath="日韩/日本/A06_個人情報の保護に関する法律についてのガイドライン（第三者提供時の確認・記録義務編）.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-GUIDE-007", jurisdiction="jp", path="all",
        doc_type="guideline",
        title="日本个人信息保护法匿名加工信息指南（2022年修订）",
        law_name_for_articles="日本个人信息保护匿名加工信息指南（2022）",
        source_org="日本个人信息保护委员会", authority_level="guidance",
        publish_date="2022-04-01", effective_date="2022-04-01", status="effective",
        url="https://www.ppc.go.jp/personalinfo/legal/",
        usage_priority="P2", notes="匿名化处理规范指南",
        module="intl-jp", category="指导文件", usage="匿名化技术参考",
        binding_force="recommended", authority="medium", publisher="日本个人信息保护委员会",
        suitable_for="匿名化处理合规", report_usage="参考引用",
        summary="规定匿名加工信息的认定标准、加工方法要求和公开义务。",
        knowledge_url="/knowledge/sources/JP-GUIDE-007",
        pdf_subpath="日韩/日本/A07_個人情報の保護に関する法律についてのガイドライン（匿名加工情報編）.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-LAW-008", jurisdiction="jp", path="all",
        doc_type="law",
        title="日本电气通信事业法（2024年修订版）",
        law_name_for_articles="日本电气通信事业法（2024）",
        source_org="日本总务省", authority_level="official",
        publish_date="2024-06-12", effective_date="2024-12-01", status="effective",
        url="https://www.soumu.go.jp/main_sosiki/joho_tsusin/",
        usage_priority="P2", notes="日本电信数据处理规则",
        module="intl-jp", category="核心法律", usage="通信数据合规审查",
        binding_force="mandatory", authority="high", publisher="日本国会",
        suitable_for="电信运营商数据合规", report_usage="可直接引用条文号",
        summary="日本电气通信事业法，规定电信运营商对通信信息的处理、保护和披露义务。",
        knowledge_url="/knowledge/sources/JP-LAW-008",
        pdf_subpath="日韩/日本/B01_電気通信事業法（2024年改正版）.pdf",
        parser=parse_japanese_articles,
    ),
    SourceDef(
        source_id="JP-LAW-009", jurisdiction="jp", path="all",
        doc_type="law",
        title="日本重要经济安保信息保护与利用法（2024年）",
        law_name_for_articles="日本重要经济安保信息保护法（2024）",
        source_org="日本内阁府", authority_level="official",
        publish_date="2024-05-10", effective_date="2025-05-15", status="effective",
        url="https://www.cao.go.jp/",
        usage_priority="P2", notes="日本经济安全保障信息保护新法",
        module="intl-jp", category="核心法律", usage="国家安全相关数据审查",
        binding_force="mandatory", authority="high", publisher="日本国会",
        suitable_for="经济安全保障数据合规", report_usage="可直接引用条文号",
        summary="日本2024年重要经济安保信息保护与利用法，建立经济安全保障视角下的机密信息制度。",
        knowledge_url="/knowledge/sources/JP-LAW-009",
        pdf_subpath="日韩/日本/C01_重要経済安保情報の保護及び活用に関する法律.pdf",
        parser=parse_japanese_articles,
    ),
]
SOURCES.extend(_JP_SOURCES)

_KR_SOURCES: list[SourceDef] = [
    # ── Korea ─────────────────────────────────────────────────────────────────
    SourceDef(
        source_id="KR-LAW-001", jurisdiction="kr", path="all",
        doc_type="law",
        title="韩国个人信息保护法（2024年修订版）",
        law_name_for_articles="韩国个人信息保护法（2024）",
        source_org="韩国个人信息保护委员会", authority_level="official",
        publish_date="2024-03-15", effective_date="2024-09-15", status="effective",
        url="https://www.pipc.go.kr/",
        usage_priority="P1", notes="韩国核心个人信息保护法",
        module="intl-kr", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="韩国国会",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="韩国2024年修订版个人信息保护法，对齐GDPR强化数据主体权利和跨境传输标准合同条款制度。",
        knowledge_url="/knowledge/sources/KR-LAW-001",
        pdf_subpath="日韩/韩国/A01_개인정보 보호법_个人信息保护法_2024年修订版.pdf",
        parser=parse_korean_articles,
    ),
    SourceDef(
        source_id="KR-REG-002", jurisdiction="kr", path="all",
        doc_type="administrative_regulation",
        title="韩国个人信息保护法施行令（2024年修订版）",
        law_name_for_articles="韩国个人信息保护法施行令（2024）",
        source_org="韩国个人信息保护委员会", authority_level="official",
        publish_date="2024-09-12", effective_date="2024-09-15", status="effective",
        url="https://www.pipc.go.kr/",
        usage_priority="P1", notes="个人信息保护法配套总统令",
        module="intl-kr", category="行政法规", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="韩国政府",
        suitable_for="合规操作", report_usage="可直接引用条文号",
        summary="韩国个人信息保护法施行令，细化数据主体权利行使程序和跨境传输合同条款细节。",
        knowledge_url="/knowledge/sources/KR-REG-002",
        pdf_subpath="日韩/韩国/A02_개인정보 보호법 시행령_个人信息保护法施行令_2024年修订版.pdf",
        parser=parse_korean_articles,
    ),
    SourceDef(
        source_id="KR-GUIDE-003", jurisdiction="kr", path="all",
        doc_type="guideline",
        title="韩国个人信息跨境传输指南（2024年）",
        law_name_for_articles="韩国个人信息跨境传输指南（2024）",
        source_org="韩国个人信息保护委员会", authority_level="guidance",
        publish_date="2024-09-15", effective_date="2024-09-15", status="effective",
        url="https://www.pipc.go.kr/",
        usage_priority="P1", notes="韩国跨境传输机制权威指南",
        module="intl-kr", category="指导文件", usage="跨境传输合规参考",
        binding_force="recommended", authority="medium", publisher="韩国个人信息保护委员会",
        suitable_for="跨境传输路径判断", report_usage="参考引用",
        summary="韩国PIPC发布的跨境传输指南，说明充分性认定、SCC和BCR三条路径的适用条件和操作流程。",
        knowledge_url="/knowledge/sources/KR-GUIDE-003",
        pdf_subpath="日韩/韩国/A03_개인정보의 국외 이전에 관한 안내서_个人信息跨境传输指南.pdf",
        parser=parse_korean_articles,
    ),
    SourceDef(
        source_id="KR-GUIDE-004", jurisdiction="kr", path="all",
        doc_type="guideline",
        title="韩国个人信息处理指南（2024年）",
        law_name_for_articles="韩国个人信息处理指南（2024）",
        source_org="韩国个人信息保护委员会", authority_level="guidance",
        publish_date="2024-10-01", effective_date="2024-10-01", status="effective",
        url="https://www.pipc.go.kr/",
        usage_priority="P2", notes="个人信息处理全流程指南",
        module="intl-kr", category="指导文件", usage="合规操作参考",
        binding_force="recommended", authority="medium", publisher="韩国个人信息保护委员会",
        suitable_for="数据处理全流程合规", report_usage="参考引用",
        summary="韩国PIPC发布的个人信息处理全流程指南，含收集、利用、提供、破弃各环节操作规范。",
        knowledge_url="/knowledge/sources/KR-GUIDE-004",
        pdf_subpath="日韩/韩国/A04_개인정보 처리 안내서_个人信息处理指南.pdf",
        parser=parse_korean_articles,
    ),
    SourceDef(
        source_id="KR-GUIDE-005", jurisdiction="kr", path="all",
        doc_type="guideline",
        title="韩国移动App个人信息保护指南（2024年）",
        law_name_for_articles="韩国移动App个人信息保护指南（2024）",
        source_org="韩国个人信息保护委员会", authority_level="guidance",
        publish_date="2024-06-01", effective_date="2024-06-01", status="effective",
        url="https://www.pipc.go.kr/",
        usage_priority="P2", notes="移动应用个人信息专项指南",
        module="intl-kr", category="指导文件", usage="移动端合规参考",
        binding_force="recommended", authority="medium", publisher="韩国个人信息保护委员会",
        suitable_for="移动应用个人信息合规", report_usage="参考引用",
        summary="针对移动应用服务提供者的个人信息保护专项指南，含权限管理和隐私政策要求。",
        knowledge_url="/knowledge/sources/KR-GUIDE-005",
        pdf_subpath="日韩/韩国/A05_모바일 앱 개인정보보호 안내서_移动App个人信息保护指南.pdf",
        parser=parse_korean_articles,
    ),
    SourceDef(
        source_id="KR-GUIDE-006", jurisdiction="kr", path="all",
        doc_type="guideline",
        title="韩国儿童个人信息保护指南（2024年）",
        law_name_for_articles="韩国儿童个人信息保护指南（2024）",
        source_org="韩国个人信息保护委员会", authority_level="guidance",
        publish_date="2024-06-01", effective_date="2024-06-01", status="effective",
        url="https://www.pipc.go.kr/",
        usage_priority="P2", notes="14岁以下儿童数据专项指南",
        module="intl-kr", category="指导文件", usage="儿童数据合规参考",
        binding_force="recommended", authority="medium", publisher="韩国个人信息保护委员会",
        suitable_for="儿童个人信息合规", report_usage="参考引用",
        summary="针对14岁以下儿童个人信息处理的专项指南，含法定代理人同意机制和最小收集原则。",
        knowledge_url="/knowledge/sources/KR-GUIDE-006",
        pdf_subpath="日韩/韩国/A06_아동 개인정보보호 안내서_儿童个人信息保护指南.pdf",
        parser=parse_korean_articles,
    ),
    SourceDef(
        source_id="KR-LAW-007", jurisdiction="kr", path="all",
        doc_type="law",
        title="韩国网络利用促进与信息保护法（2024年修订版）",
        law_name_for_articles="韩国网络利用促进与信息保护法（2024）",
        source_org="韩国科学技术信息通信部", authority_level="official",
        publish_date="2024-01-23", effective_date="2024-07-24", status="effective",
        url="https://www.msit.go.kr/",
        usage_priority="P2", notes="韩国网络信息服务专项法",
        module="intl-kr", category="核心法律", usage="网络服务合规审查",
        binding_force="mandatory", authority="high", publisher="韩国国会",
        suitable_for="网络信息服务数据合规", report_usage="可直接引用条文号",
        summary="韩国信息通信网络法，规定网络信息服务提供者的个人信息保护、青少年保护和网络安全义务。",
        knowledge_url="/knowledge/sources/KR-LAW-007",
        pdf_subpath="日韩/韩国/B01_정보통신망 이용촉진 및 정보보호 등에 관한 법률_网络利用促进与信息保护法_2024年修订版.pdf",
        parser=parse_korean_articles,
    ),
]
SOURCES.extend(_KR_SOURCES)

_HK_SOURCES: list[SourceDef] = [
    # ── Hong Kong ─────────────────────────────────────────────────────────────
    SourceDef(
        source_id="HK-LAW-001", jurisdiction="hk", path="all",
        doc_type="law",
        title="香港个人资料（私隐）条例（第486章，2021年修订版）",
        law_name_for_articles="香港个人资料（私隐）条例（第486章）",
        source_org="香港个人资料私隐专员公署", authority_level="official",
        publish_date="2021-10-05", effective_date="2021-10-05", status="effective",
        url="https://www.elegislation.gov.hk/hk/cap486",
        usage_priority="P1", notes="香港核心个人资料保护法",
        module="intl-hk", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="香港立法会",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="香港个人资料（私隐）条例，规定个人资料的收集、持有、处理和使用的六项保障资料原则，2021年新增违规转移资料刑事罪行。",
        knowledge_url="/knowledge/sources/HK-LAW-001",
        pdf_subpath="港澳台/香港/A01_Personal Data (Privacy) Ordinance Cap. 486_个人资料（私隐）条例_2021年修订版_现行合并文本.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="HK-GUIDE-002", jurisdiction="hk", path="all",
        doc_type="guideline",
        title="香港跨境资料转移（第六项保障资料原则）指引",
        law_name_for_articles="香港跨境资料转移指引",
        source_org="香港个人资料私隐专员公署", authority_level="guidance",
        publish_date="2014-12-01", effective_date="2014-12-01", status="effective",
        url="https://www.pcpd.org.hk/",
        usage_priority="P1", notes="香港跨境传输核心指引",
        module="intl-hk", category="指导文件", usage="跨境传输合规参考",
        binding_force="recommended", authority="medium", publisher="香港个人资料私隐专员公署",
        suitable_for="跨境传输路径判断", report_usage="参考引用",
        summary="香港PCPD关于保障资料第六原则（限制转移）的官方指引，说明跨境转移资料的合法条件和合同保护安排。",
        knowledge_url="/knowledge/sources/HK-GUIDE-002",
        pdf_subpath="港澳台/香港/A02_Guidance on Personal Data Protection in Cross-border Data Transfer_跨境资料转移指引.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="HK-GUIDE-003", jurisdiction="hk", path="all",
        doc_type="guideline",
        title="香港建议示范合同条款（2022年）",
        law_name_for_articles="香港建议示范合同条款（2022）",
        source_org="香港个人资料私隐专员公署", authority_level="guidance",
        publish_date="2022-11-01", effective_date="2022-11-01", status="effective",
        url="https://www.pcpd.org.hk/",
        usage_priority="P2", notes="香港跨境传输示范合同条款",
        module="intl-hk", category="指导文件", usage="合同模板参考",
        binding_force="recommended", authority="medium", publisher="香港个人资料私隐专员公署",
        suitable_for="跨境传输合同起草", report_usage="参考引用",
        summary="香港PCPD提供的跨境资料转移建议示范合同条款，含数据出口方和进口方的权利义务标准条款。",
        knowledge_url="/knowledge/sources/HK-GUIDE-003",
        pdf_subpath="港澳台/香港/A03_Recommended Model Contractual Clauses for Cross-border Transfers_建议示范合同条款_2022年版.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="HK-GUIDE-004", jurisdiction="hk", path="all",
        doc_type="guideline",
        title="香港资料泄露事故处理指引（2022年）",
        law_name_for_articles="香港资料泄露事故处理指引（2022）",
        source_org="香港个人资料私隐专员公署", authority_level="guidance",
        publish_date="2022-01-01", effective_date="2022-01-01", status="effective",
        url="https://www.pcpd.org.hk/",
        usage_priority="P2", notes="香港数据泄露响应指引",
        module="intl-hk", category="指导文件", usage="数据泄露应急参考",
        binding_force="recommended", authority="medium", publisher="香港个人资料私隐专员公署",
        suitable_for="数据泄露事件处理", report_usage="参考引用",
        summary="香港PCPD发布的资料泄露事故处理指引，含通知触发条件、通知内容和事后补救措施建议。",
        knowledge_url="/knowledge/sources/HK-GUIDE-004",
        pdf_subpath="港澳台/香港/A04_Guidance on Data Breach Handling and the Breach Notification_资料泄露事故处理指引_2022年版.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="HK-GUIDE-005", jurisdiction="hk", path="all",
        doc_type="guideline",
        title="香港使用人工智能处理个人资料的实务守则（2024年）",
        law_name_for_articles="香港AI处理个人资料实务守则（2024）",
        source_org="香港个人资料私隐专员公署", authority_level="guidance",
        publish_date="2024-06-01", effective_date="2024-06-01", status="effective",
        url="https://www.pcpd.org.hk/",
        usage_priority="P2", notes="香港AI个人资料处理指引",
        module="intl-hk", category="指导文件", usage="AI合规参考",
        binding_force="recommended", authority="medium", publisher="香港个人资料私隐专员公署",
        suitable_for="AI系统个人资料合规", report_usage="参考引用",
        summary="香港PCPD针对AI系统使用个人资料的实务守则，含AI系统生命周期各阶段的隐私保护要求。",
        knowledge_url="/knowledge/sources/HK-GUIDE-005",
        pdf_subpath="港澳台/香港/A05_Artificial Intelligence Personal Data Protection Framework_使用人工智能处理个人资料的实务守则.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="HK-LAW-006", jurisdiction="hk", path="all",
        doc_type="law",
        title="香港保护关键基础设施（电脑系统）条例（2024年）",
        law_name_for_articles="香港保护关键基础设施（电脑系统）条例（2024）",
        source_org="香港保安局", authority_level="official",
        publish_date="2024-03-19", effective_date="2025-03-01", status="effective",
        url="https://www.elegislation.gov.hk/",
        usage_priority="P1", notes="香港关键基础设施网络安全保护基本法",
        module="intl-hk", category="核心法律", usage="关键基础设施合规审查",
        binding_force="mandatory", authority="high", publisher="香港立法会",
        suitable_for="关键基础设施运营商合规", report_usage="可直接引用条文号",
        summary="香港PCSO，规定关键基础设施运营商的安全管理、事件报告和应急响应义务。",
        knowledge_url="/knowledge/sources/HK-LAW-006",
        pdf_subpath="港澳台/香港/B01_Protection of Critical Infrastructures (Computer Systems) Ordinance_保护关键基础设施（电脑系统）条例_2024年.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="HK-GUIDE-007", jurisdiction="hk", path="all",
        doc_type="guideline",
        title="香港PCSO关键基础设施运营商合规指引（2025年）",
        law_name_for_articles="香港PCSO合规指引（2025）",
        source_org="香港保安局", authority_level="guidance",
        publish_date="2025-03-01", effective_date="2025-03-01", status="effective",
        url="https://www.sb.gov.hk/",
        usage_priority="P2", notes="香港PCSO配套操作指引",
        module="intl-hk", category="指导文件", usage="关键基础设施合规操作参考",
        binding_force="recommended", authority="medium", publisher="香港保安局",
        suitable_for="关键基础设施运营商合规", report_usage="参考引用",
        summary="香港PCSO关键基础设施运营商合规指引，含安全管理计划模板和事件报告流程。",
        knowledge_url="/knowledge/sources/HK-GUIDE-007",
        pdf_subpath="港澳台/香港/B02_PCSO Compliance Guidance for Critical Infrastructure Operators_PCSO合规指引.pdf",
        parser=parse_english_sections,
    ),
]
SOURCES.extend(_HK_SOURCES)

_MO_SOURCES: list[SourceDef] = [
    # ── Macao ─────────────────────────────────────────────────────────────────
    SourceDef(
        source_id="MO-LAW-001", jurisdiction="mo", path="all",
        doc_type="law",
        title="澳门个人资料保护法（第8/2005号法律，2024年修订版）",
        law_name_for_articles="澳门个人资料保护法（第8/2005号）",
        source_org="澳门个人资料保护办公室", authority_level="official",
        publish_date="2024-07-01", effective_date="2024-07-01", status="effective",
        url="https://bo.io.gov.mo/",
        usage_priority="P1", notes="澳门核心个人资料保护法",
        module="intl-mo", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="澳门立法会",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="澳门个人资料保护法，基于欧洲数据保护指令建立个人资料保护基本框架，2024年修订强化数据主体权利和跨境传输规定。",
        knowledge_url="/knowledge/sources/MO-LAW-001",
        pdf_subpath="港澳台/澳门/A01_Lei n.° 8_2005_个人资料保护法_澳门_2024年修订版.pdf",
        parser=parse_chinese_articles,
    ),
    SourceDef(
        source_id="MO-GUIDE-002", jurisdiction="mo", path="all",
        doc_type="guideline",
        title="澳门个人资料跨境转移指引（2024年）",
        law_name_for_articles="澳门个人资料跨境转移指引（2024）",
        source_org="澳门个人资料保护办公室", authority_level="guidance",
        publish_date="2024-08-01", effective_date="2024-08-01", status="effective",
        url="https://www.gpdp.gov.mo/",
        usage_priority="P2", notes="澳门跨境传输操作指引",
        module="intl-mo", category="指导文件", usage="跨境传输合规参考",
        binding_force="recommended", authority="medium", publisher="澳门个人资料保护办公室",
        suitable_for="跨境传输路径判断", report_usage="参考引用",
        summary="澳门GPDP发布的跨境个人资料转移指引，含充分保护水平认定和合同保护安排要求。",
        knowledge_url="/knowledge/sources/MO-GUIDE-002",
        pdf_subpath="港澳台/澳门/A02_Guidance on Cross-border Transfer of Personal Data_个人资料跨境转移指引_澳门.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MO-LAW-003", jurisdiction="mo", path="all",
        doc_type="law",
        title="澳门网络安全法（第3/2019号法律）",
        law_name_for_articles="澳门网络安全法（第3/2019号）",
        source_org="澳门立法会", authority_level="official",
        publish_date="2019-04-15", effective_date="2019-10-15", status="effective",
        url="https://bo.io.gov.mo/",
        usage_priority="P2", notes="澳门网络安全基本法",
        module="intl-mo", category="核心法律", usage="网络安全合规审查",
        binding_force="mandatory", authority="high", publisher="澳门立法会",
        suitable_for="关键基础设施及网络安全合规", report_usage="可直接引用条文号",
        summary="澳门网络安全法，规定关键基础设施运营者、公共当局和关键信息基础设施的网络安全义务和事件报告制度。",
        knowledge_url="/knowledge/sources/MO-LAW-003",
        pdf_subpath="港澳台/澳门/B01_Lei n.° 3_2019_网络安全法_澳门.pdf",
        parser=parse_chinese_articles,
    ),
]
SOURCES.extend(_MO_SOURCES)

_TW_SOURCES: list[SourceDef] = [
    # ── Taiwan ────────────────────────────────────────────────────────────────
    SourceDef(
        source_id="TW-LAW-001", jurisdiction="tw", path="all",
        doc_type="law",
        title="台湾个人资料保护法（2023年修订版）",
        law_name_for_articles="台湾个人资料保护法（2023）",
        source_org="台湾个人资料保护委员会", authority_level="official",
        publish_date="2023-05-26", effective_date="2023-05-26", status="effective",
        url="https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=I0050021",
        usage_priority="P1", notes="台湾核心个人资料保护法",
        module="intl-tw", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="台湾立法院",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="台湾个人资料保护法2023年修订版，建立独立监管机构并强化数据主体权利和跨境传输管制。",
        knowledge_url="/knowledge/sources/TW-LAW-001",
        pdf_subpath="港澳台/台湾/A01_個人資料保護法_个人资料保护法_台湾_2023年修订版.pdf",
        parser=parse_chinese_articles,
    ),
    SourceDef(
        source_id="TW-REG-002", jurisdiction="tw", path="all",
        doc_type="administrative_regulation",
        title="台湾个人资料保护法施行细则（2023年修订版）",
        law_name_for_articles="台湾个人资料保护法施行细则（2023）",
        source_org="台湾法务部", authority_level="official",
        publish_date="2023-07-31", effective_date="2023-07-31", status="effective",
        url="https://law.moj.gov.tw/",
        usage_priority="P1", notes="台湾个资法配套施行细则",
        module="intl-tw", category="行政法规", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="台湾法务部",
        suitable_for="合规操作", report_usage="可直接引用条文号",
        summary="台湾个资法施行细则，细化个人资料定义、当事人权利行使程序和安全维护措施要求。",
        knowledge_url="/knowledge/sources/TW-REG-002",
        pdf_subpath="港澳台/台湾/A02_個人資料保護法施行細則_施行细则_台湾_2023年修订版.pdf",
        parser=parse_chinese_articles,
    ),
    SourceDef(
        source_id="TW-REG-003", jurisdiction="tw", path="all",
        doc_type="administrative_regulation",
        title="台湾个人资料保护法之特定目的及个人资料之类别（2023年修订版）",
        law_name_for_articles="台湾个资法特定目的及类别（2023）",
        source_org="台湾法务部", authority_level="official",
        publish_date="2023-07-31", effective_date="2023-07-31", status="effective",
        url="https://law.moj.gov.tw/",
        usage_priority="P2", notes="台湾个资法特定目的和类别编码表",
        module="intl-tw", category="行政法规", usage="数据分类参考",
        binding_force="mandatory", authority="high", publisher="台湾法务部",
        suitable_for="数据目的和类别合规标注", report_usage="可直接引用条文号",
        summary="台湾个资法指定的特定目的代码（001-182）和个人资料类别代码（C001-C211）权威对照表。",
        knowledge_url="/knowledge/sources/TW-REG-003",
        pdf_subpath="港澳台/台湾/A03_個人資料保護法之特定目的及個人資料之類別_特定目的及类别_台湾_2023年修订版.pdf",
        parser=parse_chinese_articles,
    ),
    SourceDef(
        source_id="TW-LAW-004", jurisdiction="tw", path="all",
        doc_type="law",
        title="台湾资通安全管理法（2021年修订版）",
        law_name_for_articles="台湾资通安全管理法（2021）",
        source_org="台湾数位部", authority_level="official",
        publish_date="2021-06-09", effective_date="2022-01-01", status="effective",
        url="https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=A0030297",
        usage_priority="P1", notes="台湾政府机关网络安全基本法",
        module="intl-tw", category="核心法律", usage="网络安全合规审查",
        binding_force="mandatory", authority="high", publisher="台湾立法院",
        suitable_for="政府机关及关键基础设施安全合规", report_usage="可直接引用条文号",
        summary="台湾资通安全管理法，规定政府机关和特定非政府机关的资安管理义务、事件通报和稽核制度。",
        knowledge_url="/knowledge/sources/TW-LAW-004",
        pdf_subpath="港澳台/台湾/B01_資通安全管理法_资通安全管理法_台湾_2021年修订版.pdf",
        parser=parse_chinese_articles,
    ),
    SourceDef(
        source_id="TW-REG-005", jurisdiction="tw", path="all",
        doc_type="administrative_regulation",
        title="台湾资通安全管理法施行细则（2022年版）",
        law_name_for_articles="台湾资通安全管理法施行细则（2022）",
        source_org="台湾数位部", authority_level="official",
        publish_date="2022-01-01", effective_date="2022-01-01", status="effective",
        url="https://law.moj.gov.tw/",
        usage_priority="P2", notes="资通安全管理法配套施行细则",
        module="intl-tw", category="行政法规", usage="网络安全合规操作参考",
        binding_force="mandatory", authority="high", publisher="台湾数位部",
        suitable_for="资安管理体系建设", report_usage="可直接引用条文号",
        summary="台湾资通安全管理法施行细则，细化资安等级分级标准、稽核频率和事件通报时限。",
        knowledge_url="/knowledge/sources/TW-REG-005",
        pdf_subpath="港澳台/台湾/B02_資通安全管理法施行細則_施行细则_台湾_2022年版.pdf",
        parser=parse_chinese_articles,
    ),
]
SOURCES.extend(_TW_SOURCES)

_MY_SOURCES: list[SourceDef] = [
    # ── Malaysia ──────────────────────────────────────────────────────────────
    SourceDef(
        source_id="MY-LAW-001", jurisdiction="my", path="all",
        doc_type="law",
        title="马来西亚个人数据保护法 2010（2023年修订版）",
        law_name_for_articles="马来西亚个人数据保护法（PDPA 2010）",
        source_org="马来西亚个人数据保护局", authority_level="official",
        publish_date="2023-10-17", effective_date="2024-01-01", status="effective",
        url="https://pdp.com.my/",
        usage_priority="P1", notes="马来西亚核心个人数据保护法",
        module="intl-my", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="马来西亚国会",
        suitable_for="路径判断、合规审查", report_usage="可直接引用条文号",
        summary="马来西亚个人数据保护法2023修订版，强化数据主体权利，引入强制数据泄露通知和数据保护官制度。",
        knowledge_url="/knowledge/sources/MY-LAW-001",
        pdf_subpath="马来西亚/A01_Personal Data Protection Act 2010_个人数据保护法_2023年修订版.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MY-LAW-002", jurisdiction="my", path="all",
        doc_type="law",
        title="马来西亚个人数据保护（修订）法 2024",
        law_name_for_articles="马来西亚个人数据保护修订法（2024）",
        source_org="马来西亚个人数据保护局", authority_level="official",
        publish_date="2024-10-31", effective_date="2025-01-01", status="effective",
        url="https://pdp.com.my/",
        usage_priority="P1", notes="马来西亚PDPA 2024修订，引入DPO强制要求",
        module="intl-my", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="马来西亚国会",
        suitable_for="路径判断、DPO合规", report_usage="可直接引用条文号",
        summary="马来西亚2024年PDPA修订法，强制要求指定数据保护官（DPO），明确数据泄露72小时通知义务。",
        knowledge_url="/knowledge/sources/MY-LAW-002",
        pdf_subpath="马来西亚/A02_Personal Data Protection (Amendment) Act 2024_个人数据保护（修订）法_2024年.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MY-REG-003", jurisdiction="my", path="all",
        doc_type="administrative_regulation",
        title="马来西亚个人数据保护标准 2015",
        law_name_for_articles="马来西亚个人数据保护标准（2015）",
        source_org="马来西亚个人数据保护局", authority_level="official",
        publish_date="2015-11-17", effective_date="2016-05-01", status="effective",
        url="https://pdp.com.my/",
        usage_priority="P2", notes="马来西亚PDPA配套技术标准",
        module="intl-my", category="行政法规", usage="合规技术参考",
        binding_force="mandatory", authority="high", publisher="马来西亚个人数据保护局",
        suitable_for="数据安全技术合规", report_usage="可直接引用条文号",
        summary="马来西亚个人数据保护标准，规定个人数据处理和安全的技术最低标准要求。",
        knowledge_url="/knowledge/sources/MY-REG-003",
        pdf_subpath="马来西亚/A03_Personal Data Protection Standards 2015_个人数据保护标准_马来西亚.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MY-REG-004", jurisdiction="my", path="all",
        doc_type="administrative_regulation",
        title="马来西亚个人数据保护条例（注册）2013",
        law_name_for_articles="马来西亚个人数据保护注册条例（2013）",
        source_org="马来西亚个人数据保护局", authority_level="official",
        publish_date="2013-11-07", effective_date="2013-11-15", status="effective",
        url="https://pdp.com.my/",
        usage_priority="P2", notes="数据处理者注册制度条例",
        module="intl-my", category="行政法规", usage="合规操作参考",
        binding_force="mandatory", authority="high", publisher="马来西亚个人数据保护局",
        suitable_for="数据处理者注册合规", report_usage="可直接引用条文号",
        summary="马来西亚个人数据保护注册条例，规定适用行业数据处理者的强制注册义务和程序。",
        knowledge_url="/knowledge/sources/MY-REG-004",
        pdf_subpath="马来西亚/A04_Personal Data Protection Regulations (Registration) 2013_个人数据保护（注册）条例_马来西亚.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MY-REG-005", jurisdiction="my", path="all",
        doc_type="administrative_regulation",
        title="马来西亚个人数据保护条例（豁免）2023",
        law_name_for_articles="马来西亚个人数据保护豁免条例（2023）",
        source_org="马来西亚个人数据保护局", authority_level="official",
        publish_date="2023-10-17", effective_date="2024-01-01", status="effective",
        url="https://pdp.com.my/",
        usage_priority="P2", notes="PDPA豁免情形配套条例",
        module="intl-my", category="行政法规", usage="豁免情形判断",
        binding_force="mandatory", authority="high", publisher="马来西亚个人数据保护局",
        suitable_for="数据处理豁免情形判断", report_usage="可直接引用条文号",
        summary="规定马来西亚PDPA适用豁免的具体情形，包括家庭用途、新闻、研究和政府行为等。",
        knowledge_url="/knowledge/sources/MY-REG-005",
        pdf_subpath="马来西亚/A05_Personal Data Protection Regulations (Exemption) 2023_个人数据保护（豁免）条例_马来西亚.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MY-LAW-006", jurisdiction="my", path="all",
        doc_type="law",
        title="马来西亚网络安全法 2024",
        law_name_for_articles="马来西亚网络安全法（2024）",
        source_org="马来西亚国家网络安全局", authority_level="official",
        publish_date="2024-06-26", effective_date="2025-01-01", status="effective",
        url="https://nacsa.gov.my/",
        usage_priority="P1", notes="马来西亚网络安全基本法",
        module="intl-my", category="核心法律", usage="审查基准",
        binding_force="mandatory", authority="high", publisher="马来西亚国会",
        suitable_for="关键基础设施及网络安全合规", report_usage="可直接引用条文号",
        summary="马来西亚2024年网络安全法，建立国家网络安全框架，规定关键信息基础设施保护义务和网络安全事件强制报告制度。",
        knowledge_url="/knowledge/sources/MY-LAW-006",
        pdf_subpath="马来西亚/B01_Cyber Security Act 2024_网络安全法_马来西亚_2024年.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MY-REG-007", jurisdiction="my", path="all",
        doc_type="administrative_regulation",
        title="马来西亚网络安全法国家关键信息基础设施条例 2024",
        law_name_for_articles="马来西亚NCII条例（2024）",
        source_org="马来西亚国家网络安全局", authority_level="official",
        publish_date="2024-12-01", effective_date="2025-01-01", status="effective",
        url="https://nacsa.gov.my/",
        usage_priority="P2", notes="马来西亚NCII认定和保护配套条例",
        module="intl-my", category="行政法规", usage="关键基础设施合规操作参考",
        binding_force="mandatory", authority="high", publisher="马来西亚国家网络安全局",
        suitable_for="NCII运营商认定和合规", report_usage="可直接引用条文号",
        summary="规定马来西亚国家关键信息基础设施（NCII）的认定标准、安全管理要求和事件通报流程。",
        knowledge_url="/knowledge/sources/MY-REG-007",
        pdf_subpath="马来西亚/B02_Cyber Security (National Critical Information Infrastructure) Regulations 2024_NCII条例_马来西亚.pdf",
        parser=parse_english_sections,
    ),
    SourceDef(
        source_id="MY-REG-008", jurisdiction="my", path="all",
        doc_type="administrative_regulation",
        title="马来西亚网络安全法网络安全服务提供者条例 2024",
        law_name_for_articles="马来西亚网络安全服务提供者条例（2024）",
        source_org="马来西亚国家网络安全局", authority_level="official",
        publish_date="2024-12-01", effective_date="2025-01-01", status="effective",
        url="https://nacsa.gov.my/",
        usage_priority="P2", notes="马来西亚网络安全服务提供者许可制度",
        module="intl-my", category="行政法规", usage="网络安全服务合规参考",
        binding_force="mandatory", authority="high", publisher="马来西亚国家网络安全局",
        suitable_for="网络安全服务提供者许可合规", report_usage="可直接引用条文号",
        summary="规定马来西亚网络安全服务提供者的许可证申请资格、服务范围和持续合规义务。",
        knowledge_url="/knowledge/sources/MY-REG-008",
        pdf_subpath="马来西亚/B03_Cyber Security (Cybersecurity Service Provider) Regulations 2024_网络安全服务提供者条例_马来西亚.pdf",
        parser=parse_english_sections,
    ),
]
SOURCES.extend(_MY_SOURCES)


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def load_existing_source_ids() -> set[str]:
    if not SOURCES_CSV.exists():
        return set()
    with SOURCES_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {row["source_id"] for row in reader}


def load_existing_article_keys() -> set[tuple[str, str]]:
    if not ARTICLES_JSONL.exists():
        return set()
    keys: set[tuple[str, str]] = set()
    with ARTICLES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                keys.add((obj["source_id"], str(obj.get("article_ref") or obj.get("article_no", ""))))
            except (json.JSONDecodeError, KeyError):
                pass
    return keys


def write_sources_csv(sources: list[SourceDef], existing_ids: set[str], dry_run: bool) -> int:
    """Append new source rows to sources.csv. Returns count written."""
    new_sources = [s for s in sources if s.source_id not in existing_ids]
    if not new_sources:
        print("  sources.csv: no new sources to add (all IDs already present)")
        return 0

    # Read header from existing file
    with SOURCES_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

    count = 0
    for s in new_sources:
        row = {
            "source_id": s.source_id,
            "layer": s.layer,
            "jurisdiction": s.jurisdiction,
            "path": s.path,
            "doc_type": s.doc_type,
            "title": s.title,
            "source_org": s.source_org,
            "authority_level": s.authority_level,
            "publish_date": s.publish_date,
            "effective_date": s.effective_date,
            "status": s.status,
            "url": s.url,
            "snapshot_path": s.snapshot_path,
            "usage_priority": s.usage_priority,
            "notes": s.notes,
            "module": s.module,
            "category": s.category,
            "usage": s.usage,
            "binding_force": s.binding_force,
            "authority": s.authority,
            "publisher": s.publisher,
            "suitable_for": s.suitable_for,
            "report_usage": s.report_usage,
            "summary": s.summary,
            "knowledge_url": s.knowledge_url,
            "origin_path": s.origin_path,
        }
        # Fill any extra fields passed in s.extra
        row.update(s.extra)
        # Ensure all CSV columns exist
        for fn in fieldnames:
            row.setdefault(fn, "")

        if dry_run:
            print(f"  [DRY-RUN] would add source: {s.source_id} — {s.title}")
        else:
            with SOURCES_CSV.open("a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writerow(row)
            print(f"  + source: {s.source_id} — {s.title}")
        count += 1

    return count


def write_articles_jsonl(
    sources: list[SourceDef],
    existing_keys: set[tuple[str, str]],
    dry_run: bool,
) -> tuple[int, int, int]:
    """Extract + append article entries. Returns (sources_processed, articles_added, sources_skipped)."""
    added = 0
    skipped = 0
    processed = 0

    for s in sources:
        pdf_path = PDF_BASE / s.pdf_subpath
        if not pdf_path.exists():
            print(f"  WARN PDF not found, skipping articles: {pdf_path}")
            skipped += 1
            continue

        raw_text = extract_pdf_text(pdf_path)
        if not raw_text.strip():
            print(f"  INFO PDF non-extractable (image-based?): {s.source_id}")
            skipped += 1
            continue

        articles = s.parser(raw_text)
        if not articles:
            print(f"  INFO no articles parsed for {s.source_id}")
            skipped += 1
            continue

        processed += 1
        for article_no, article_text in articles:
            key = (s.source_id, article_no)
            if key in existing_keys:
                continue
            entry = {
                "source_id": s.source_id,
                "article_ref": article_no,
                "law_name": s.law_name_for_articles,
                "content": article_text[:2000],  # cap to avoid huge entries
                "jurisdiction": s.jurisdiction,
            }
            if dry_run:
                print(f"  [DRY-RUN] would add article: {s.source_id} 第{article_no}条")
            else:
                with ARTICLES_JSONL.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                existing_keys.add(key)
            added += 1

    return processed, added, skipped


# ---------------------------------------------------------------------------
# Parser implementations  (filled in here to keep file self-contained)
# ---------------------------------------------------------------------------

def kanji_to_int(s: str) -> int:
    """Convert kanji number string like '二十三' to int 23."""
    # Simple left-to-right with positional multipliers
    result = 0
    temp = 0
    for ch in s:
        if ch.isdigit():
            temp = int(ch)
        elif ch in _KANJI:
            v = _KANJI[ch]
            if v >= 10:
                temp = temp or 1
                result += temp * v
                temp = 0
            else:
                temp = v
    result += temp
    return result


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  WARN pdftotext failed for {pdf_path.name}: {e}")
        return ""


def parse_chinese_articles(text: str) -> list[tuple[str, str]]:
    """Match 第N条 / 第 N 條 with arabic or kanji numerals."""
    pattern = re.compile(
        r"第\s*([0-9一二三四五六七八九十百千]+)\s*[条條]([^\n]*(?:\n(?!第\s*[0-9一二三四五六七八九十百千]+\s*[条條])[^\n]*)*)",
        re.MULTILINE,
    )
    results: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        raw_no = m.group(1).strip()
        # try arabic first, then kanji
        try:
            no = str(int(raw_no))
        except ValueError:
            try:
                no = str(kanji_to_int(raw_no))
            except Exception:
                no = raw_no
        body = (m.group(0)).strip()
        results.append((no, body[:500]))
    return results


def parse_japanese_articles(text: str) -> list[tuple[str, str]]:
    """Match 第N条 with kanji or arabic numerals (Japanese law style)."""
    pattern = re.compile(
        r"第([一二三四五六七八九十百千\d]+)条([^\n]*(?:\n(?!第[一二三四五六七八九十百千\d]+条)[^\n]*)*)",
        re.MULTILINE,
    )
    results: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        raw_no = m.group(1).strip()
        try:
            no = str(int(raw_no))
        except ValueError:
            try:
                no = str(kanji_to_int(raw_no))
            except Exception:
                no = raw_no
        body = m.group(0).strip()
        results.append((no, body[:500]))
    return results


def parse_korean_articles(text: str) -> list[tuple[str, str]]:
    """Match 제N조 (Korean article markers)."""
    pattern = re.compile(
        r"제(\d+)조[（(〔\[]?([^\n]*)(?:\n(?!제\d+조)[^\n]*)*",
        re.MULTILINE,
    )
    results: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        no = m.group(1)
        body = m.group(0).strip()
        results.append((no, body[:500]))
    return results


def parse_english_sections(text: str) -> list[tuple[str, str]]:
    """Match ^N. Section title (English numbered sections)."""
    pattern = re.compile(
        r"^(\d+)\.\s+\S[^\n]*(?:\n(?!\d+\.\s)[^\n]*)*",
        re.MULTILINE,
    )
    results: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        no = m.group(1)
        body = m.group(0).strip()
        results.append((no, body[:500]))
    return results


def parse_malay_sections(text: str) -> list[tuple[str, str]]:
    """Match Seksyen N (Malay) or fall back to numbered sections."""
    pattern = re.compile(
        r"^Seksyen\s+(\d+)\b[^\n]*(?:\n(?!Seksyen\s+\d+)[^\n]*)*",
        re.MULTILINE,
    )
    results = [(m.group(1), m.group(0).strip()[:500]) for m in pattern.finditer(text)]
    if not results:
        results = parse_english_sections(text)
    return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest regional law sources and articles into catalog/registry."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be written without modifying any files.",
    )
    parser.add_argument(
        "--jurisdiction", "-j",
        help="Only process sources for this jurisdiction code (e.g. jp, kr, sg).",
    )
    args = parser.parse_args()

    sources = SOURCES
    if args.jurisdiction:
        sources = [s for s in sources if s.jurisdiction == args.jurisdiction.lower()]
        print(f"Filtered to jurisdiction={args.jurisdiction}: {len(sources)} sources")

    print(f"\n=== ingest_regional_laws {'[DRY-RUN] ' if args.dry_run else ''}===")
    print(f"  Total source defs to process: {len(sources)}")

    existing_ids = load_existing_source_ids()
    existing_keys = load_existing_article_keys()
    print(f"  Existing sources in CSV   : {len(existing_ids)}")
    print(f"  Existing article keys     : {len(existing_keys)}")

    # 1. Update sources.csv
    print("\n[1/2] Writing sources.csv …")
    n_sources = write_sources_csv(sources, existing_ids, args.dry_run)

    # 2. Update regulation_articles.jsonl
    print("\n[2/2] Extracting articles from PDFs …")
    processed, n_articles, n_skipped = write_articles_jsonl(sources, existing_keys, args.dry_run)

    print(f"\n=== Summary ===")
    print(f"  Sources added : {n_sources}")
    print(f"  PDFs processed: {processed}")
    print(f"  Articles added: {n_articles}")
    print(f"  PDFs skipped  : {n_skipped} (image-based or missing)")
    if args.dry_run:
        print("\n  [DRY-RUN] No files were modified.")


# ---------------------------------------------------------------------------
# Patch pdf_subpaths to match actual filenames on disk
# (generated from: find resources/new/知识库补充 -name "*.pdf" | sort)
# ---------------------------------------------------------------------------
_PDF_PATH_FIXES: dict[str, str] = {
    # ── Japan ──
    "JP-LAW-001":   "日韩/日本/A01_个人信息保护法_日本e-Gov官方PDF_现行版.pdf",
    "JP-REG-002":   "日韩/日本/A03_个人信息保护法施行规则_日本e-Gov官方.pdf",
    "JP-REG-003":   "日韩/日本/A02_个人信息保护法施行令_日本e-Gov官方.pdf",
    "JP-GUIDE-004": "日韩/日本/A04_个人信息保护基本方针_日本政府PPC官方PDF.pdf",
    "JP-GUIDE-005": "日韩/日本/A05_个人信息保护法指引（通则）_PPC官方PDF_2026-06-14施行.pdf",
    "JP-GUIDE-006": "日韩/日本/A06_境外第三方提供指引_PPC官方PDF_2025-12修订.pdf",
    "JP-GUIDE-007": "日韩/日本/A07_欧盟英国充分性接收数据补充规则_PPC官方PDF.pdf",
    "JP-LAW-008":   "日韩/日本/B01_2_网络安全基本法_日本e-Gov官方 2026年10月1日生效.pdf",
    # JP-LAW-009: no matching PDF on disk yet — will be skipped gracefully
    # ── Korea ──
    "KR-LAW-001":   "日韩/韩国/A01_个人信息保护法_国家法令信息中心官方PDF_现行版.pdf",
    "KR-REG-002":   "日韩/韩国/A02_个人信息保护法施行令_国家法令信息中心官方PDF_2026-05-19.pdf",
    "KR-GUIDE-003": "日韩/韩国/A03_个人信息跨境转移运行等规定_国家法令信息中心官方.pdf",
    "KR-GUIDE-004": "日韩/韩国/A04_2_个人信息安全措施标准_正文_PIPC官方附件_2026-07-01.pdf",
    "KR-GUIDE-005": "日韩/韩国/A06_标准个人信息保护指针_PIPC官方PDF_2025-04-11.pdf",
    # KR-GUIDE-006: no matching PDF yet
    "KR-LAW-007":   "日韩/韩国/B01_信息通信基础保护法(法律)(第20068号)_2025-01-24.pdf",
    # ── Hong Kong ──
    "HK-LAW-001":   "港澳台/香港/A01_《個人資料（私隱）條例》（第486章）_香港电子法例现行数据转制PDF_版本日期2022-10-01.pdf",
    "HK-GUIDE-002": "港澳台/香港/A02_《保障個人資料：跨境資料轉移指引》_2014年12月_监管指引.pdf",
    "HK-GUIDE-003": "港澳台/香港/A03_《跨境資料轉移指引：建議合約條文範本》_2022年5月_监管指引.pdf",
    "HK-GUIDE-004": "港澳台/香港/A04_《粤港澳大湾区（内地、香港）个人信息跨境流动标准合同实施指引》_含标准合同附件_2023年12月.pdf",
    "HK-GUIDE-005": "港澳台/香港/A05_《跨境资料转移指引_粤港澳大湾区（内地、香港）个人信息跨境流动标准合同》_2023年12月_监管指引.pdf",
    "HK-LAW-006":   "港澳台/香港/B01_《保护关键基础设施（电脑系统）条例》（第653章）_香港电子法例现行数据转制PDF_2026年1月1日生效.pdf",
    "HK-GUIDE-007": "港澳台/香港/B02_第653章《实务守则（通用）》_2026年第1版_限指定营运者适用.pdf",
    # ── Macao ──
    "MO-LAW-001":   "港澳台/澳门/A01_第8-2005号法律《个人资料保护法》_中葡双语官方公报版.pdf",
    "MO-GUIDE-002": "港澳台/澳门/A02_《粤港澳大湾区（内地、澳门）个人信息跨境流动标准合同实施指引》_含标准合同附件_2024年9月.pdf",
    "MO-LAW-003":   "港澳台/澳门/B01_第13-2019号法律《网络安全法》_中葡双语官方公报版.pdf",
    # ── Taiwan ──
    "TW-LAW-001":   "港澳台/台湾/A01_《个人资料保护法》_官方最新公布文本_含尚未生效条文提示.pdf",
    "TW-REG-002":   "港澳台/台湾/A02_《个人资料保护法部分条文修正对照表》_2025年11月11日公布_尚未施行.pdf",
    "TW-REG-003":   "港澳台/台湾/A03_《个人资料保护法施行细则》_官方现行版_2016年3月2日修正.pdf",
    "TW-LAW-004":   "港澳台/台湾/B01_《资通安全管理法》_2025年9月24日修正_2025年12月1日施行.pdf",
    "TW-REG-005":   "港澳台/台湾/B02_《资通安全管理法施行细则》_2026年1月5日修正版.pdf",
    # ── Malaysia ──
    "MY-LAW-001":   "马来西亚/A01_Personal Data Protection Act 2010_个人数据保护法_基础法官方文本_2022版.pdf",
    "MY-LAW-002":   "马来西亚/A02_Personal Data Protection (Amendment) Act 2024_个人数据保护修正法_全条已生效.pdf",
    "MY-REG-003":   "马来西亚/A05_Personal Data Protection Standard 2015_个人数据保护标准_现行法定标准.pdf",
    "MY-REG-004":   "马来西亚/A04_Personal Data Protection Regulations 2013_个人数据保护条例_PU(A)335.pdf",
    "MY-REG-005":   "马来西亚/A03_Personal Data Protection (Amendment) Act 2024_Appointment of Date of Coming into Operation_生效日期公告_PU(B)522.pdf",
    "MY-LAW-006":   "马来西亚/B01_Cyber Security Act 2024_网络安全法_Act854.pdf",
    "MY-REG-007":   "马来西亚/B02_Cyber Security (Notification of Cyber Security Incident) Regulations 2024_网络安全事件通知条例_PU(A)220.pdf",
    "MY-REG-008":   "马来西亚/B03_Cyber Security (Period for Cyber Security Risk Assessment and Audit) Regulations 2024_网络安全风险评估和审计期限条例_PU(A)219.pdf",
}

for _s in SOURCES:
    if _s.source_id in _PDF_PATH_FIXES:
        _s.pdf_subpath = _PDF_PATH_FIXES[_s.source_id]

if __name__ == "__main__":
    main()
