#!/usr/bin/env python3
"""Generate the JP/KR pending-source proposal table (expert sign-off required).

WHY THIS EXISTS
---------------
The identity audit found eight PDFs in the JP/KR reference package that are real
documents but have NO correct source_id binding today:

  - four are orphaned (B01_1, A04_1) or bound to the WRONG source (B01_2, A04_2,
    A06, B01, A04, A07);
  - they therefore need a NEW source_id (or a version/annex relation to a new
    parent source) before the unified rebuild (Phase 4) can be run.

This is a *proposal* table, not an adjudication: it recommends metadata
(title/doc_type/authority/binding_force/layer/category) and a relation type for
each PDF. It is grounded in the extracted first-page text, but the final source_id
naming and any enum extension is a legal sign-off decision.

Output: status/check/task065/jp_kr_pending_source_proposals.csv

Relation enum:
  independent : create a standalone source_id
  version     : create a version of an independent source (history/effective pair)
  annex       : attach as an annex to an independent source
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_CSV = ROOT / "status" / "check" / "task065" / "jp_kr_pending_source_proposals.csv"

# (proposal_id, relation, parent_source_id, pdf_relpath, suggested_source_id,
#  suggested_title, suggested_doc_type, suggested_authority, suggested_authority_level,
#  suggested_binding_force, suggested_layer, suggested_category, rationale)
# All suggestions are DRAFT and must be confirmed by a legal-domain reviewer.
PROPOSALS: list[dict[str, str]] = [
    {
        "proposal_id": "P-JP-01",
        "relation": "independent",
        "parent_source_id": "",
        "pdf_relpath": "resources/legal/sources/jp/references/A04_个人信息保护基本方针_日本政府PPC官方PDF.pdf",
        "suggested_source_id": "JP-POLICY-001",
        "suggested_title": "日本个人信息保护基本方针（令和4年一部改正）",
        "suggested_doc_type": "policy",
        "suggested_authority": "medium",
        "suggested_authority_level": "guidance",
        "suggested_binding_force": "recommended",
        "suggested_layer": "legal_rules",
        "suggested_category": "指导文件",
        "rationale": "PDF 首页为『個人情報の保護に関する基本方針（閣議決定）』，系基于个人信息保护法第7条第1项的政府基本方针，"
        "当前被 JP-GUIDE-004『通则指南』错绑；性质为 policy（政府方针），已新增 policy 枚举，source_id 前缀建议从 GUIDE 调整为 POLICY，待专家定名。",
    },
    {
        "proposal_id": "P-JP-02",
        "relation": "independent",
        "parent_source_id": "",
        "pdf_relpath": "resources/legal/sources/jp/references/A07_欧盟英国充分性接收数据补充规则_PPC官方PDF.pdf",
        "suggested_source_id": "JP-GUIDE-009",
        "suggested_title": "日本基于充分性决定接收欧盟/英国转移个人数据的补充规则",
        "suggested_doc_type": "guideline",
        "suggested_authority": "medium",
        "suggested_authority_level": "guidance",
        "suggested_binding_force": "recommended",
        "suggested_layer": "legal_rules",
        "suggested_category": "指导文件",
        "rationale": "PDF 首页为『Supplementary Rules … transferred from the EU and the United Kingdom based on an Adequacy Decision』，"
        "当前被 JP-GUIDE-007『匿名加工信息指南』错绑；系 PPC 公布的补充规则，与匿名加工信息完全无关。",
    },
    {
        "proposal_id": "P-JP-03",
        "relation": "independent",
        "parent_source_id": "",
        "pdf_relpath": "resources/legal/sources/jp/references/B01_2_网络安全基本法_日本e-Gov官方 2026年10月1日生效.pdf",
        "suggested_source_id": "JP-LAW-010",
        "suggested_title": "日本网络安全基本法（平成26年法律第104号，2026年10月1日施行版）",
        "suggested_doc_type": "law",
        "suggested_authority": "high",
        "suggested_authority_level": "official",
        "suggested_binding_force": "mandatory",
        "suggested_layer": "legal_rules",
        "suggested_category": "核心法律",
        "rationale": "PDF 首页为『サイバーセキュリティ基本法（平成二十六年法律第百四号）』，当前被 JP-LAW-008『电气通信事业法』错绑；"
        "与电气通信事业法是两部不同法律，须新建独立 source。",
    },
    {
        "proposal_id": "P-JP-04",
        "relation": "version",
        "parent_source_id": "JP-LAW-010",
        "pdf_relpath": "resources/legal/sources/jp/references/B01_1_网络安全基本法_日本e-Gov官方 2026年10月1日失效.pdf",
        "suggested_source_id": "JP-LAW-010",
        "suggested_title": "日本网络安全基本法（2026年10月1日失效版）",
        "suggested_doc_type": "law",
        "suggested_authority": "high",
        "suggested_authority_level": "official",
        "suggested_binding_force": "mandatory",
        "suggested_layer": "legal_rules",
        "suggested_category": "核心法律",
        "rationale": "PDF 首页为『サイバーセキュリティ基本法』，是 P-JP-03 的历史失效版本；当前检索仅允许生效版，历史时点审计才允许查询失效版。",
    },
    {
        "proposal_id": "P-KR-01",
        "relation": "independent",
        "parent_source_id": "",
        "pdf_relpath": "resources/legal/sources/kr/references/A04_2_个人信息安全措施标准_正文_PIPC官方附件_2026-07-01.pdf",
        "suggested_source_id": "KR-STD-007",
        "suggested_title": "韩国个人信息安全措施标准（고시 제2026-9호）",
        "suggested_doc_type": "technical_standard",
        "suggested_authority": "medium",
        "suggested_authority_level": "guidance",
        "suggested_binding_force": "recommended",
        "suggested_layer": "legal_rules",
        "suggested_category": "指导文件",
        "rationale": "PDF 首页为『개인정보의 안전성 확보조치 기준（安全措施标准）』，当前被 KR-GUIDE-004『个人信息处理指南』错绑；"
        "系 PIPC 告示（고시），性质为 technical_standard（技术标准），已新增 technical_standard 枚举，source_id 前缀建议从 GUIDE 调整为 STD，待专家定名。",
    },
    {
        "proposal_id": "P-KR-02",
        "relation": "annex",
        "parent_source_id": "KR-STD-007",
        "pdf_relpath": "resources/legal/sources/kr/references/A04_1_个人信息安全措施标准_附表_风险降低保护措施示例_PIPC官方附件_2026-07-01.pdf",
        "suggested_source_id": "KR-STD-007",
        "suggested_title": "韩国个人信息安全措施标准附表（风险降低保护措施示例，第6条之2相关）",
        "suggested_doc_type": "technical_standard",
        "suggested_authority": "medium",
        "suggested_authority_level": "guidance",
        "suggested_binding_force": "recommended",
        "suggested_layer": "legal_rules",
        "suggested_category": "指导文件",
        "rationale": "PDF 首页为『【별표】위험을 감소시킬 수 있는 보호조치 예시（제6조의2 관련）』，系 P-KR-01 正文的附表；"
        "应作为附件（relation=annex）而非独立法律，引用应能表达为正文第6条之2附表。",
    },
    {
        "proposal_id": "P-KR-03",
        "relation": "independent",
        "parent_source_id": "",
        "pdf_relpath": "resources/legal/sources/kr/references/A06_标准个人信息保护指针_PIPC官方PDF_2025-04-11.pdf",
        "suggested_source_id": "KR-GUIDE-008",
        "suggested_title": "韩国标准个人信息保护指针（고시 제2025-4호）",
        "suggested_doc_type": "guideline",
        "suggested_authority": "medium",
        "suggested_authority_level": "guidance",
        "suggested_binding_force": "recommended",
        "suggested_layer": "legal_rules",
        "suggested_category": "指导文件",
        "rationale": "PDF 首页为『표준 개인정보 보호지침（标准个人信息保护指针）』，当前被 KR-GUIDE-005『移动App指南』错绑；"
        "系 PIPC 告示（고시），与移动App指南不同，须新建独立 source。",
    },
    {
        "proposal_id": "P-KR-04",
        "relation": "independent",
        "parent_source_id": "",
        "pdf_relpath": "resources/legal/sources/kr/references/B01_信息通信基础保护法(法律)(第20068号)_2025-01-24.pdf",
        "suggested_source_id": "KR-LAW-008",
        "suggested_title": "韩国信息通信基础保护法（법률 제20068호）",
        "suggested_doc_type": "law",
        "suggested_authority": "high",
        "suggested_authority_level": "official",
        "suggested_binding_force": "mandatory",
        "suggested_layer": "legal_rules",
        "suggested_category": "核心法律",
        "rationale": "PDF 首页为『정보통신기반 보호법（信息通信基础保护法）』，当前被 KR-LAW-007『网络利用促进与信息保护法』错绑；"
        "与网络利用促进与信息保护法（정보통신망법）是两部不同法律，须新建独立 source。",
    },
]

COLUMNS = [
    "proposal_id",
    "relation",
    "parent_source_id",
    "PDF path",
    "PDF SHA-256",
    "PDF 首页原文标题",
    "PDF 发布机关",
    "PDF 版本/生效日期",
    "suggested_source_id",
    "suggested_title",
    "suggested_doc_type",
    "suggested_authority",
    "suggested_authority_level",
    "suggested_binding_force",
    "suggested_layer",
    "suggested_category",
    "依据",
    "专家意见",
    "审核人",
    "审核日期",
]

HUMAN_COLUMNS = {"专家意见", "审核人", "审核日期"}

LEGAL_RELATIONS = {"independent", "version", "annex"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _extract_first_page_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - pypdf is a declared dependency
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    if not reader.pages:
        return ""
    try:
        return (reader.pages[0].extract_text() or "").strip()
    except Exception:
        return ""


def _first_lines(text: str, limit: int = 3) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " / ".join(lines[:limit])


def _detect_publisher(text: str, filename: str) -> str:
    signals = [
        ("閣議決定", "日本政府（内阁）"),
        ("個人情報保護委員会", "日本个人信息保护委员会（PPC）"),
        ("PPC", "日本个人信息保护委员会（PPC）"),
        ("개인정보보호위원회", "韩国个人信息保护委员会（PIPC）"),
        ("PIPC", "韩国个人信息保护委员会（PIPC）"),
        ("국가법령정보센터", "韩国国家法令信息中心"),
        ("법제처", "韩国法制处"),
        ("과학기술정보통신부", "韩国科学技术信息通信部"),
        ("国家法令信息中心", "韩国国家法令信息中心"),
    ]
    haystack = f"{text[:600]}\n{filename}"
    seen: set[str] = set()
    out: list[str] = []
    for signal, label in signals:
        if signal in haystack and label not in seen:
            seen.add(label)
            out.append(label)
    return "、".join(out)


def _extract_version_from_filename(filename: str) -> str:
    tokens = ["现行版", "失效", "生效", "施行", "修订", "附表", "正文"]
    return "、".join(t for t in tokens if t in filename)


def _load_existing_human_signoff() -> dict[str, dict[str, str]]:
    if not OUT_CSV.exists():
        return {}
    with OUT_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        out: dict[str, dict[str, str]] = {}
        for row in reader:
            pid = (row.get("proposal_id") or "").strip()
            out[pid] = {col: (row.get(col) or "").strip() for col in HUMAN_COLUMNS}
        return out


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for prop in PROPOSALS:
        relpath = prop["pdf_relpath"]
        p = (ROOT / relpath).resolve()
        sha = ""
        text = ""
        if p.exists():
            sha = _sha256(p)
            text = _extract_first_page_text(p)
        rows.append({
            "proposal_id": prop["proposal_id"],
            "relation": prop["relation"],
            "parent_source_id": prop["parent_source_id"],
            "PDF path": relpath,
            "PDF SHA-256": sha,
            "PDF 首页原文标题": _first_lines(text),
            "PDF 发布机关": _detect_publisher(text, p.name) if p.exists() else "",
            "PDF 版本/生效日期": _extract_version_from_filename(p.name) if p.exists() else "",
            "suggested_source_id": prop["suggested_source_id"],
            "suggested_title": prop["suggested_title"],
            "suggested_doc_type": prop["suggested_doc_type"],
            "suggested_authority": prop["suggested_authority"],
            "suggested_authority_level": prop["suggested_authority_level"],
            "suggested_binding_force": prop["suggested_binding_force"],
            "suggested_layer": prop["suggested_layer"],
            "suggested_category": prop["suggested_category"],
            "依据": prop["rationale"],
            "专家意见": "",
            "审核人": "",
            "审核日期": "",
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write the proposal CSV (preserving human sign-off columns)")
    ap.add_argument("--check", action="store_true", help="fail if the CSV is missing or structurally invalid")
    args = ap.parse_args()

    rows = build_rows()
    human = _load_existing_human_signoff()
    for row in rows:
        prior = human.get(row["proposal_id"], {})
        for col in HUMAN_COLUMNS:
            row[col] = prior.get(col, "")

    if args.check:
        if not OUT_CSV.exists():
            print(f"FAIL proposal CSV missing: {OUT_CSV.relative_to(ROOT)}")
            return 2
        existing = _load_existing_human_signoff()
        if not existing:
            print("FAIL proposal CSV has no rows")
            return 2
        for row in rows:
            if row["relation"] not in LEGAL_RELATIONS:
                print(f"FAIL illegal relation {row['relation']!r} for {row['proposal_id']}")
                return 2
            if row["relation"] in {"version", "annex"} and not row["parent_source_id"]:
                print(f"FAIL {row['proposal_id']} {row['relation']} missing parent_source_id")
                return 2
        print(f"OK   proposal CSV present with {len(rows)} draft rows (human sign-off preserved)")
        return 0

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    payload = buf.getvalue()

    if args.write:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        OUT_CSV.write_text(payload, encoding="utf-8")
        print(f"OK   wrote {len(rows)} rows -> {OUT_CSV.relative_to(ROOT)}")
        return 0

    sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
