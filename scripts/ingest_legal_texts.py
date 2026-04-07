"""
一次性法律文本入库脚本
将 doc/v3/数据跨境中美欧法律文本 下的 PDF/DOCX 按条文切分，
追加写入 doc/knowledge/normalized/regulation_articles.jsonl
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pypdf
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "doc/knowledge/normalized/regulation_articles.jsonl"
SRC_DIR = ROOT / "doc/v3/数据跨境中美欧法律文本"

# ──────────────────────────────────────────────────────────────────────────────
# 通用工具
# ──────────────────────────────────────────────────────────────────────────────

def extract_pdf_text(path: Path) -> str:
    reader = pypdf.PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(path: Path) -> str:
    try:
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        # Fallback for old binary .doc files: extract printable ASCII runs
        data = path.read_bytes()
        chunks = re.findall(rb'[\x20-\x7e]{20,}', data)
        return "\n".join(c.decode("latin-1", errors="replace") for c in chunks)


def make_keywords(law_name: str, article_ref: str, content: str, extras: list[str]) -> list[str]:
    kws = [law_name, article_ref] + extras
    # 从内容取前几个有意义的词组（bigram-friendly）
    words = re.findall(r'[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,12}', content[:300])
    seen: set[str] = set(kws)
    for w in words:
        if w not in seen:
            kws.append(w)
            seen.add(w)
        if len(kws) >= 12:
            break
    return kws


def existing_ids() -> set[str]:
    ids: set[str] = set()
    if JSONL_PATH.exists():
        for line in JSONL_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ids.add(json.loads(line)["article_id"])
    return ids


def append_entries(entries: list[dict]) -> int:
    existing = existing_ids()
    new_entries = [e for e in entries if e["article_id"] not in existing]
    if not new_entries:
        return 0
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        for e in new_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return len(new_entries)


# ──────────────────────────────────────────────────────────────────────────────
# 中文条文切分（第一条、第二条… 或 第1条、第2条…）
# ──────────────────────────────────────────────────────────────────────────────

CN_NUM = r'[一二三四五六七八九十百千万零〇0-9]'

def split_cn_articles(text: str) -> list[tuple[str, str]]:
    """返回 [(article_ref, content), ...]，content 含 article_ref 前缀"""
    pattern = re.compile(rf'(第{CN_NUM}{{1,6}}条(?:[　\s][^\n]{{0,30}})?)')
    parts = pattern.split(text)
    results: list[tuple[str, str]] = []
    i = 1
    while i < len(parts) - 1:
        ref = parts[i].strip()
        body = (ref + " " + parts[i + 1]).strip()
        # 过滤过短（目录项）和重复引用
        if len(body) > 15:
            results.append((ref, body))
        i += 2
    return results


# ──────────────────────────────────────────────────────────────────────────────
# 英文条文切分（Article X / Clause X / Section X）
# ──────────────────────────────────────────────────────────────────────────────

def split_en_articles(text: str, keyword: str = "Article") -> list[tuple[str, str]]:
    pattern = re.compile(rf'({keyword}\s+\d+[\s\S]{{0,60}}?)(?=\n)', re.IGNORECASE)
    # 用更宽泛方式：按 keyword + 数字 切分
    parts = re.split(rf'(?={keyword}\s+\d+)', text, flags=re.IGNORECASE)
    results: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(rf'({keyword}\s+\d+)', part, re.IGNORECASE)
        if m:
            ref = m.group(1).strip()
            body = part[:1200].strip()
            if len(body) > 30:
                results.append((ref, body))
    return results


# ──────────────────────────────────────────────────────────────────────────────
# 1. 个人信息出境认证办法（中国，PDF，第X条中文数字）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_cert_measures() -> list[dict]:
    path = SRC_DIR / "中国框架/个人信息出境认证办法.pdf"
    text = extract_pdf_text(path)
    articles = split_cn_articles(text)
    entries = []
    for i, (ref, content) in enumerate(articles, start=1):
        entries.append({
            "article_id": f"CN-LAW-007-{i:03d}",
            "jurisdiction": "cn",
            "path": "scc",
            "law_name": "个人信息出境认证办法",
            "article_ref": ref,
            "content": content[:1000],
            "keywords": make_keywords("个人信息出境认证办法", ref, content,
                                      ["认证", "个人信息出境", "认证机构"]),
            "source_url": "https://www.cac.gov.cn/2025-10/14/c_1730000000000000.htm",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/中国框架/个人信息出境认证办法.pdf",
            "publish_date": "2025-10-14",
            "effective_date": "2026-01-01",
            "status": "effective",
            "source_id": "CN-LAW-007",
            "doc_type": "administrative_regulation",
            "usage_priority": "P0",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 2. GDPR 中文（丁晓东译，DOCX，第X条阿拉伯数字）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_gdpr_cn() -> list[dict]:
    path = SRC_DIR / "欧盟框架/1.GDPR_中文（丁晓东译）.docx"
    text = extract_docx_text(path)
    # GDPR中文版用阿拉伯数字：第1条、第2条…
    pattern = re.compile(r'(第\d{1,3}条(?:\s+[^\n]{0,60})?)')
    parts = pattern.split(text)

    # 章节信息辅助表（article_no -> chapter/path）
    def path_for(no: int) -> str:
        if no in (35,): return "dpia"
        if no in (46, 47, 48, 49): return "bcr|tia|scc"
        if 44 <= no <= 49: return "tia|scc"
        return "all"

    entries = []
    i = 1
    seq = 0
    while i < len(parts) - 1:
        ref = parts[i].strip()
        body = (ref + " " + parts[i + 1]).strip()
        if len(body) > 20:
            no_match = re.search(r'第(\d+)条', ref)
            no = int(no_match.group(1)) if no_match else 0
            seq += 1
            entries.append({
                "article_id": f"EU-LAW-002-{seq:03d}",
                "jurisdiction": "eu",
                "path": path_for(no),
                "law_name": "GDPR（一般数据保护条例）中文版",
                "article_ref": ref.split('\n')[0][:40],
                "content": body[:1000],
                "keywords": make_keywords("GDPR", ref, body,
                                          ["个人数据", "数据处理", "数据主体", "控制者", "处理者"]),
                "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
                "snapshot_path": "doc/v3/数据跨境中美欧法律文本/欧盟框架/1.GDPR_中文（丁晓东译）.docx",
                "publish_date": "2016-04-27",
                "effective_date": "2018-05-25",
                "status": "effective",
                "source_id": "EU-LAW-002",
                "doc_type": "law",
                "usage_priority": "P0",
                "layer": "legal_rules",
            })
        i += 2
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 3. EU Standard Contractual Clauses（英文，DOC → docx 读取）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_eu_scc() -> list[dict]:
    path = SRC_DIR / "欧盟框架/EN Standard Contractual Clauses.doc"
    text = extract_docx_text(path)
    # SCC 用 "Clause X" 结构
    articles = split_en_articles(text, keyword="Clause")
    if len(articles) < 3:
        articles = split_en_articles(text, keyword="Article")
    entries = []
    for i, (ref, content) in enumerate(articles, start=1):
        entries.append({
            "article_id": f"EU-LAW-003-{i:03d}",
            "jurisdiction": "eu",
            "path": "scc|tia",
            "law_name": "EU Standard Contractual Clauses (2021)",
            "article_ref": ref,
            "content": content[:1000],
            "keywords": make_keywords("EU SCC", ref, content,
                                      ["standard contractual clauses", "transfer", "third country",
                                       "data exporter", "data importer"]),
            "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32021D0914",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/欧盟框架/EN Standard Contractual Clauses.doc",
            "publish_date": "2021-06-04",
            "effective_date": "2021-09-27",
            "status": "effective",
            "source_id": "EU-LAW-003",
            "doc_type": "regulatory_instrument",
            "usage_priority": "P0",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 4. EDPB Recommendations 1/2022 on BCR-C（英文，PDF）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_bcr_recommendations() -> list[dict]:
    path = SRC_DIR / "欧盟框架/recommendations_20221_bcr-c_edpb_en.pdf"
    text = extract_pdf_text(path)
    # 用编号段落切分：数字列表项（1.1、1.2 等）和段落标题
    # 先尝试按主要章节切（数字+空格+大写）
    pattern = re.compile(r'(\d+(?:\.\d+)?\s+[A-Z][^\n]{10,80})')
    parts = pattern.split(text)

    entries = []
    i = 1
    seq = 0
    while i < len(parts) - 1:
        ref = parts[i].strip()
        body = (ref + "\n" + parts[i + 1]).strip()
        if len(body) > 60 and not ref.startswith("VERSION"):
            seq += 1
            entries.append({
                "article_id": f"EU-LAW-004-{seq:03d}",
                "jurisdiction": "eu",
                "path": "bcr",
                "law_name": "EDPB Recommendations 1/2022 on BCR-C",
                "article_ref": ref[:80],
                "content": body[:1000],
                "keywords": make_keywords("EDPB BCR-C Recommendations", ref, body,
                                          ["BCR", "binding corporate rules", "controller",
                                           "Article 47", "supervisory authority"]),
                "source_url": "https://edpb.europa.eu/our-work-tools/our-documents/recommendations/recommendations-12022_en",
                "snapshot_path": "doc/v3/数据跨境中美欧法律文本/欧盟框架/recommendations_20221_bcr-c_edpb_en.pdf",
                "publish_date": "2022-11-14",
                "effective_date": "2023-06-20",
                "status": "effective",
                "source_id": "EU-LAW-004",
                "doc_type": "guide",
                "usage_priority": "P1",
                "layer": "legal_rules",
            })
        i += 2
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 5. California Privacy Rights Act of 2020（中文版 PDF，Section X）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_cpra() -> list[dict]:
    path = SRC_DIR / "美国框架/The California Privacy Rights Act of 2020.pdf"
    text = extract_pdf_text(path)
    # 切分方式：Section X（含英文）或 §X
    articles = split_en_articles(text, keyword="Section")
    if len(articles) < 3:
        # 尝试 § 符号
        parts = re.split(r'(?=§\s*\d+)', text)
        articles = []
        for part in parts:
            m = re.match(r'(§\s*\d+)', part)
            if m:
                articles.append((m.group(1).strip(), part[:1200].strip()))

    entries = []
    for i, (ref, content) in enumerate(articles, start=1):
        entries.append({
            "article_id": f"US-LAW-003-{i:03d}",
            "jurisdiction": "us",
            "path": "cpra",
            "law_name": "California Privacy Rights Act (CPRA) 2020",
            "article_ref": ref,
            "content": content[:1000],
            "keywords": make_keywords("CPRA CCPA", ref, content,
                                      ["consumer", "personal information", "sensitive",
                                       "opt-out", "sale", "sharing", "business"]),
            "source_url": "https://cppa.ca.gov/regulations/",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/美国框架/The California Privacy Rights Act of 2020.pdf",
            "publish_date": "2020-11-03",
            "effective_date": "2023-01-01",
            "status": "effective",
            "source_id": "US-LAW-003",
            "doc_type": "law",
            "usage_priority": "P0",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 6. Executive Order 14117（英文，PDF，Section X）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_eo14117() -> list[dict]:
    path = SRC_DIR / "美国框架/Executive_Order_14117.pdf"
    text = extract_pdf_text(path)
    articles = split_en_articles(text, keyword="Sec")
    if len(articles) < 2:
        articles = split_en_articles(text, keyword="Section")
    entries = []
    for i, (ref, content) in enumerate(articles, start=1):
        entries.append({
            "article_id": f"US-LAW-004-{i:03d}",
            "jurisdiction": "us",
            "path": "cn_flow",
            "law_name": "Executive Order 14117 (Feb 2024)",
            "article_ref": ref,
            "content": content[:1000],
            "keywords": make_keywords("EO 14117", ref, content,
                                      ["bulk sensitive data", "countries of concern",
                                       "restricted transactions", "national security",
                                       "covered person"]),
            "source_url": "https://www.federalregister.gov/documents/2024/03/01/2024-04594/preventing-access-to-americans-bulk-sensitive-personal-data-and-united-states-government-related",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/美国框架/Executive_Order_14117.pdf",
            "publish_date": "2024-02-28",
            "effective_date": "2024-02-28",
            "status": "effective",
            "source_id": "US-LAW-004",
            "doc_type": "executive_order",
            "usage_priority": "P0",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 7. EDPB Guidelines Article 3 & Chapter V – transfer examples（英文，PDF）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_transfer_guidelines() -> list[dict]:
    path = SRC_DIR / "欧盟框架/Transfer_Art 3 & Ch V Guidelines.pdf"
    text = extract_pdf_text(path)
    parts = re.split(r'(?=Example\s+\d+[\.:]\s)', text, flags=re.IGNORECASE)
    entries = []
    for i, part in enumerate(parts, start=1):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'(Example\s+\d+[^\n]{0,120})', part, re.IGNORECASE)
        ref = m.group(1).strip()[:100] if m else f"Example {i}"
        body = part[:1200]
        if len(body) < 40:
            continue
        entries.append({
            "article_id": f"EU-GUIDE-005-{i:03d}",
            "jurisdiction": "eu",
            "path": "tia|scc",
            "law_name": "EDPB Guidelines on Article 3 & Chapter V (Transfer Examples)",
            "article_ref": ref,
            "content": body,
            "keywords": make_keywords("EDPB transfer guidelines", ref, body,
                                      ["Chapter V", "transfer", "third country",
                                       "controller", "processor", "Article 3"]),
            "source_url": "https://edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052021-interplay-between-article-3-and-chapter_en",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/欧盟框架/Transfer_Art 3 & Ch V Guidelines.pdf",
            "publish_date": "2021-11-18",
            "effective_date": "2021-11-18",
            "status": "effective",
            "source_id": "EU-GUIDE-005",
            "doc_type": "guide",
            "usage_priority": "P1",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 8. Complete Handbook for Cross-Border Transfers（英文，PDF，11章）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_complete_handbook() -> list[dict]:
    path = SRC_DIR / "欧盟框架/The Complete Handbook for Cross Border Transfers.pdf"
    text = extract_pdf_text(path)
    # Split on chapter headings: standalone "N. Title" lines
    parts = re.split(r'(?m)^(\d{1,2})\.\s+([A-Z][A-Za-z ,&/\-]{5,80})\s*$', text)
    entries = []
    seq = 0
    i = 1
    while i + 2 < len(parts):
        chap_num = parts[i].strip()
        chap_title = parts[i + 1].strip()
        body = (chap_title + "\n" + parts[i + 2]).strip()
        i += 3
        if len(body) < 100 or chap_title.endswith("...") or "Endnotes" in chap_title:
            continue
        seq += 1
        ref = f"Chapter {chap_num}: {chap_title}"
        entries.append({
            "article_id": f"EU-GUIDE-006-{seq:03d}",
            "jurisdiction": "eu",
            "path": "scc|tia|bcr",
            "law_name": "Complete Handbook for Cross-Border Transfers (2022)",
            "article_ref": ref[:80],
            "content": body[:1200],
            "keywords": make_keywords("cross-border transfer handbook", ref, body,
                                      ["SCC", "standard contractual clauses", "EEA",
                                       "controller", "processor", "transfer"]),
            "source_url": "https://www.gtlaw.com/en/insights/2022/5/the-complete-handbook-for-cross-border-transfers",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/欧盟框架/The Complete Handbook for Cross Border Transfers.pdf",
            "publish_date": "2022-05-01",
            "effective_date": "2022-05-01",
            "status": "effective",
            "source_id": "EU-GUIDE-006",
            "doc_type": "guide",
            "usage_priority": "P1",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 9. ICO DPIA Template（英文，DOCX，Step 1-7）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_ico_dpia_template() -> list[dict]:
    path = SRC_DIR / "欧盟框架/2.2 ICO_DPIA_Temple.docx"
    text = extract_docx_text(path)
    parts = re.split(r'(?=Step\s+\d+[:\s])', text, flags=re.IGNORECASE)
    entries = []
    for i, part in enumerate(parts, start=1):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'(Step\s+\d+[^\n]{0,80})', part, re.IGNORECASE)
        ref = m.group(1).strip()[:80] if m else f"Step {i}"
        body = part[:1200]
        if len(body) < 30:
            continue
        entries.append({
            "article_id": f"EU-GUIDE-007-{i:03d}",
            "jurisdiction": "eu",
            "path": "dpia",
            "law_name": "ICO Sample DPIA Template",
            "article_ref": ref,
            "content": body,
            "keywords": make_keywords("ICO DPIA template", ref, body,
                                      ["DPIA", "data protection impact assessment",
                                       "risk", "processing", "necessity", "proportionality"]),
            "source_url": "https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr/accountability-and-governance/data-protection-impact-assessments/",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/欧盟框架/2.2 ICO_DPIA_Temple.docx",
            "publish_date": "2018-05-25",
            "effective_date": "2018-05-25",
            "status": "effective",
            "source_id": "EU-GUIDE-007",
            "doc_type": "guide",
            "usage_priority": "P1",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 10. TIA Template（英文，DOCX，Step 1-6，CNIL法国）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_tia_template() -> list[dict]:
    path = SRC_DIR / "欧盟框架/TIA - Template.docx"
    text = extract_docx_text(path)
    parts = re.split(r'(?=Step\s+\d+\s*[–\-—:])', text, flags=re.IGNORECASE)
    entries = []
    for i, part in enumerate(parts, start=1):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'(Step\s+\d+[^\n]{0,80})', part, re.IGNORECASE)
        ref = m.group(1).strip()[:80] if m else f"Step {i}"
        body = part[:1200]
        if len(body) < 30:
            continue
        entries.append({
            "article_id": f"EU-GUIDE-008-{i:03d}",
            "jurisdiction": "eu",
            "path": "tia",
            "law_name": "TIA Template – CNIL Transfer Impact Assessment Guide",
            "article_ref": ref,
            "content": body,
            "keywords": make_keywords("TIA template CNIL", ref, body,
                                      ["TIA", "transfer impact assessment", "third country",
                                       "supplementary measures", "Article 46", "EDPB"]),
            "source_url": "https://www.cnil.fr/en/transfer-impact-assessment-tia",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/欧盟框架/TIA - Template.docx",
            "publish_date": "2024-02-12",
            "effective_date": "2024-02-12",
            "status": "effective",
            "source_id": "EU-GUIDE-008",
            "doc_type": "guide",
            "usage_priority": "P1",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 11. Trans-Atlantic Data Privacy Framework Overview（英文，PDF，单页）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_tadpf() -> list[dict]:
    path = SRC_DIR / "美国框架/Trans-Atlantic_Data_Privacy_Framework.pdf.pdf"
    text = extract_pdf_text(path).strip()
    if len(text) < 50:
        return []
    # Split by bullet sections: "Key principles" / "Benefits" / "Next steps"
    sections = re.split(r'(?m)^(Key principles|Benefits of the deal|Next steps)', text)
    entries = []
    seq = 0
    if sections:
        # First chunk is intro
        intro = sections[0].strip()
        if len(intro) > 30:
            seq += 1
            entries.append({
                "article_id": f"US-EU-001-{seq:03d}",
                "jurisdiction": "eu",
                "path": "scc|tia",
                "law_name": "Trans-Atlantic Data Privacy Framework (TADPF) Overview",
                "article_ref": "Overview",
                "content": intro[:1200],
                "keywords": make_keywords("TADPF Trans-Atlantic Data Privacy Framework",
                                          "Overview", intro,
                                          ["adequacy", "Schrems II", "EU-US", "intelligence",
                                           "data flows", "privacy"]),
                "source_url": "https://commission.europa.eu/document/fa09cbad-dd7d-4684-ae60-be03fcb0fddf_en",
                "snapshot_path": "doc/v3/数据跨境中美欧法律文本/美国框架/Trans-Atlantic_Data_Privacy_Framework.pdf.pdf",
                "publish_date": "2022-03-25",
                "effective_date": "2022-03-25",
                "status": "effective",
                "source_id": "US-EU-001",
                "doc_type": "guide",
                "usage_priority": "P1",
                "layer": "legal_rules",
            })
    i = 1
    while i + 1 < len(sections):
        heading = sections[i].strip()
        body = (heading + "\n" + sections[i + 1]).strip()
        i += 2
        if len(body) < 30:
            continue
        seq += 1
        entries.append({
            "article_id": f"US-EU-001-{seq:03d}",
            "jurisdiction": "eu",
            "path": "scc|tia",
            "law_name": "Trans-Atlantic Data Privacy Framework (TADPF) Overview",
            "article_ref": heading[:60],
            "content": body[:1200],
            "keywords": make_keywords("TADPF Trans-Atlantic Data Privacy Framework",
                                      heading, body,
                                      ["adequacy", "Schrems II", "EU-US", "intelligence",
                                       "data flows", "privacy"]),
            "source_url": "https://commission.europa.eu/document/fa09cbad-dd7d-4684-ae60-be03fcb0fddf_en",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/美国框架/Trans-Atlantic_Data_Privacy_Framework.pdf.pdf",
            "publish_date": "2022-03-25",
            "effective_date": "2022-03-25",
            "status": "effective",
            "source_id": "US-EU-001",
            "doc_type": "guide",
            "usage_priority": "P1",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 12. CLOUD Act（英文，PDF，SEC. X）
# ──────────────────────────────────────────────────────────────────────────────

def ingest_cloud_act() -> list[dict]:
    path = SRC_DIR / "美国框架/cloud_act.pdf"
    text = extract_pdf_text(path)
    # PDF uses "SEC. 101." format; split on that pattern
    parts = re.split(r'(?=SEC\.\s+\d+)', text, flags=re.IGNORECASE)
    articles = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r'(SEC\.\s+\d+[^\n]{0,80})', part, re.IGNORECASE)
        if m:
            ref = m.group(1).strip()
            body = part[:1200].strip()
            if len(body) > 30:
                articles.append((ref, body))
    entries = []
    for i, (ref, content) in enumerate(articles, start=1):
        entries.append({
            "article_id": f"US-LAW-005-{i:03d}",
            "jurisdiction": "us",
            "path": "cn_flow",
            "law_name": "CLOUD Act (Clarifying Lawful Overseas Use of Data Act, 2018)",
            "article_ref": ref,
            "content": content[:1000],
            "keywords": make_keywords("CLOUD Act", ref, content,
                                      ["overseas data", "communications service provider",
                                       "stored communications", "national security",
                                       "law enforcement", "foreign government"]),
            "source_url": "https://www.congress.gov/bill/115th-congress/house-bill/4943",
            "snapshot_path": "doc/v3/数据跨境中美欧法律文本/美国框架/cloud_act.pdf",
            "publish_date": "2018-03-23",
            "effective_date": "2018-03-23",
            "status": "effective",
            "source_id": "US-LAW-005",
            "doc_type": "law",
            "usage_priority": "P1",
            "layer": "legal_rules",
        })
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    tasks = [
        ("个人信息出境认证办法",       ingest_cert_measures),
        ("GDPR 中文版（丁晓东译）",    ingest_gdpr_cn),
        ("EU Standard Contractual Clauses", ingest_eu_scc),
        ("EDPB BCR-C Recommendations 1/2022", ingest_bcr_recommendations),
        ("CPRA 2020",                  ingest_cpra),
        ("Executive Order 14117",      ingest_eo14117),
        ("EDPB Transfer Guidelines (Art.3 & Ch.V)", ingest_transfer_guidelines),
        ("Complete Handbook for Cross-Border Transfers", ingest_complete_handbook),
        ("ICO DPIA Template",          ingest_ico_dpia_template),
        ("TIA Template (CNIL)",        ingest_tia_template),
        ("Trans-Atlantic Data Privacy Framework", ingest_tadpf),
        ("CLOUD Act (2018)",           ingest_cloud_act),
    ]

    total = 0
    for name, fn in tasks:
        try:
            entries = fn()
            added = append_entries(entries)
            print(f"  ✅ {name}: 解析 {len(entries)} 条，新增 {added} 条")
            total += added
        except Exception as exc:
            print(f"  ❌ {name}: {exc}", file=sys.stderr)

    print(f"\n总计新增 {total} 条到知识库")

    # 验证总量
    count = sum(1 for l in JSONL_PATH.read_text(encoding="utf-8").splitlines() if l.strip())
    print(f"知识库当前总条数: {count}")


if __name__ == "__main__":
    main()
