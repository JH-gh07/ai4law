#!/usr/bin/env python3
"""Generate the JP/KR source identity adjudication draft (human sign-off required).

WHY THIS EXISTS
---------------
The JP/KR reference package shows a systemic title<->PDF misalignment (see
`status/check/task065/T10_区域知识库闭环_验收报告.md` section 四.4 and the
task065 remediation plan). The affected sources are already quarantined with
`review_status=metadata_review_required`, so they no longer feed formal legal
conclusions or article-number citation.

This script produces the human review table `jp_kr_source_adjudication.csv`. It is
**only a draft generator**:

  - code-computed columns (CSV metadata, PDF SHA-256, first-page title/publisher/
    version, current-binding diagnosis, suggested disposition) are re-derived on
    every run;
  - human columns (`专家意见`, `审核人`, `审核日期`) are preserved from the previous
    CSV so a re-run never clobbers expert sign-off.

The final disposition decision is a legal act, not a code act. The suggested
`建议处置` values here come from the plan's Phase 3 analysis and must be confirmed
by a legal-domain reviewer before any metadata/registry/index rebuild.

Disposition enum (authoritative):
  confirm_binding, correct_metadata, replace_pdf, create_new_source,
  link_as_version, link_as_annex, quarantine, retire
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

SOURCES_CSV = ROOT / "resources" / "legal" / "catalog" / "sources.csv"
OUT_CSV = ROOT / "status" / "check" / "task065" / "jp_kr_source_adjudication.csv"

# Sources isolated from formal legal conclusions / article-number citation. This is
# the Phase 1 quarantine list, extended by the identity audit: the original 8 plus
# JP-GUIDE-006 (JP guide block is shifted by one) and KR-LAW-007 (bound to a
# DIFFERENT Korean law). Order is stable for the CSV.
QUARANTINED_SOURCE_IDS = [
    "JP-LAW-008",
    "JP-LAW-009",
    "JP-GUIDE-004",
    "JP-GUIDE-005",
    "JP-GUIDE-006",
    "JP-GUIDE-007",
    "KR-GUIDE-004",
    "KR-GUIDE-005",
    "KR-GUIDE-006",
    "KR-LAW-007",
]

# Metadata-only review rows: the binding is substantially correct (the PDF matches
# the source's subject), but a metadata field is stale or mis-typed. These stay
# citable but are surfaced for expert correction.
REVIEW_ONLY_SOURCE_IDS = [
    "JP-REG-003",
    "KR-GUIDE-003",
]

# Orphan PDFs that exist on disk but have no source_id binding. The plan requires
# these two be resolved as a version relation or an annex relation, not as new laws.
ORPHAN_PDFS = {
    "ORPHAN-JP-B01_1": "resources/legal/sources/jp/references/B01_1_网络安全基本法_日本e-Gov官方 2026年10月1日失效.pdf",
    "ORPHAN-KR-A04_1": "resources/legal/sources/kr/references/A04_1_个人信息安全措施标准_附表_风险降低保护措施示例_PIPC官方附件_2026-07-01.pdf",
}

# Current-binding diagnosis + suggested disposition. Diagnoses are grounded in the
# extracted first-page text of each PDF (see the acceptance report audit section).
# These are DRAFT suggestions; final disposition is a legal sign-off.
ADJUDICATION_DRAFT: dict[str, tuple[str, str]] = {
    "JP-LAW-008": (
        "CSV『电气通信事业法』vs PDF 首页『サイバーセキュリティ基本法（平成26年法律第104号）』，"
        "为两部不同法律（电信事业法≠网络安全基本法）；真正电气通信事业法 PDF 缺失，"
        "B01_2 网络安全基本法需另行建立 source 或改名",
        "create_new_source",
    ),
    "JP-LAW-009": (
        "CSV 有记录但无对应 PDF，正文无法核验；须找到官方 PDF、登记官方 HTML 快照，或降级为 "
        "metadata-only/停用，不能把其他日本安全相关 PDF 临时绑定过去",
        "quarantine",
    ),
    "JP-GUIDE-004": (
        "CSV『通则指南』vs PDF 首页『個人情報の保護に関する基本方針（阁议决定）』，基本方针≠通则；"
        "正确 PDF 应为 A05『ガイドライン（通則編）』，JP 指南块整体偏移一位",
        "correct_metadata",
    ),
    "JP-GUIDE-005": (
        "CSV『境外提供指南』vs PDF 首页『ガイドライン（通則編）』，通则≠境外；"
        "正确 PDF 应为 A06『外国第三者提供編』",
        "correct_metadata",
    ),
    "JP-GUIDE-006": (
        "CSV『第三方提供记录指南』vs PDF 首页『ガイドライン（外国第三者提供編）』，境外提供≠记录；"
        "正确 PDF（第三者提供记录编）缺失，A06 应归属 JP-GUIDE-005",
        "correct_metadata",
    ),
    "JP-GUIDE-007": (
        "CSV『匿名加工信息指南』vs PDF 首页『Supplementary Rules … EU/UK Adequacy Decision』，"
        "完全无关；正确 PDF（匿名加工信息编）缺失，A07 欧盟/英国充分性需另行建立 source",
        "correct_metadata",
    ),
    "KR-GUIDE-004": (
        "CSV『个人信息处理指南』vs PDF 首页『개인정보의 안전성 확보조치 기준（安全措施标准）』，"
        "类型与内容不符；A04_2 安全措施标准需另行建立 source 或改名",
        "correct_metadata",
    ),
    "KR-GUIDE-005": (
        "CSV『移动App指南』vs PDF 首页『표준 개인정보 보호지침（标准个人信息保护指针）』，"
        "疑似错绑；A06 标准指针需另行建立 source 或改名",
        "correct_metadata",
    ),
    "KR-GUIDE-006": (
        "CSV 有记录但无对应 PDF；A06 首页实际为『标准个人信息保护指针（2025-04-11）』，不能充当儿童指南；"
        "须先确认『儿童个人信息保护指南』是否真实存在、官方名称与版本",
        "quarantine",
    ),
    "KR-LAW-007": (
        "CSV『网络利用促进与信息保护法』（=정보통신망 이용촉진 및 정보보호 등에 관한 법률）vs "
        "PDF 首页『정보통신기반 보호법（信息通信基础保护法）』，为两部不同韩国法律，高风险错绑；"
        "正确 PDF 缺失，B01 信息通信基础保护法需另行建立 source",
        "create_new_source",
    ),
    "JP-REG-003": (
        "绑定基本正确（施行令→A02），但 CSV『2021年政令第311号』与 PDF 首页『平成15年政令第507号』"
        "不一致，政令号疑似陈旧/版本混淆，须专家核对",
        "correct_metadata",
    ),
    "KR-GUIDE-003": (
        "主题正确（跨境转移→A03），但 PDF 首页为『개인정보 국외 이전 운영 등에 관한 규정』（规定/고시），"
        "CSV 标题『指南』与 doc_type『guideline』均误，应改为规定/告示类",
        "correct_metadata",
    ),
    "ORPHAN-JP-B01_1": (
        "日本《网络安全基本法》失效版，无 source 归属；应与 B01_2 建立版本关系，"
        "当前检索仅允许 B01_2，历史时点审计才允许查询失效版",
        "link_as_version",
    ),
    "ORPHAN-KR-A04_1": (
        "韩国《个人信息安全措施标准》附表，非独立法律；应作为 A04_2 正文附件（relation=annex），"
        "引用应能表达为正文第六条之二附表",
        "link_as_annex",
    ),
}

COLUMNS = [
    "source_id",
    "CSV title",
    "CSV doc_type",
    "CSV authority",
    "CSV publish_date",
    "CSV effective_date",
    "PDF path",
    "PDF SHA-256",
    "PDF 首页原文标题",
    "PDF 发布机关",
    "PDF 版本/生效日期",
    "当前绑定结论",
    "建议处置",
    "专家意见",
    "审核人",
    "审核日期",
]

HUMAN_COLUMNS = {"专家意见", "审核人", "审核日期"}

LEGAL_DISPOSITIONS = {
    "confirm_binding", "correct_metadata", "replace_pdf", "create_new_source",
    "link_as_version", "link_as_annex", "quarantine", "retire",
}


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


def _load_csv_rows() -> dict[str, dict[str, str]]:
    if not SOURCES_CSV.exists():
        return {}
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as fh:
        return {row.get("source_id", "").strip(): row for row in csv.DictReader(fh)}


def _load_existing_human_signoff() -> dict[str, dict[str, str]]:
    if not OUT_CSV.exists():
        return {}
    with OUT_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        out: dict[str, dict[str, str]] = {}
        for row in reader:
            sid = (row.get("source_id") or "").strip()
            out[sid] = {col: (row.get(col) or "").strip() for col in HUMAN_COLUMNS}
        return out


def _row_for_source(sid: str, row: dict[str, str]) -> dict[str, str]:
    snapshot = (row.get("snapshot_path") or "").strip()
    pdf_path = snapshot
    sha = ""
    first_lines = ""
    publisher = ""
    version = ""
    if snapshot:
        p = (ROOT / snapshot).resolve()
        if p.exists():
            sha = _sha256(p)
            text = _extract_first_page_text(p)
            first_lines = _first_lines(text)
            publisher = _detect_publisher(text, p.name)
            version = _extract_version_from_filename(p.name)
    diagnosis, disposition = ADJUDICATION_DRAFT.get(sid, ("", ""))
    return {
        "source_id": sid,
        "CSV title": (row.get("title") or "").strip(),
        "CSV doc_type": (row.get("doc_type") or "").strip(),
        "CSV authority": (row.get("authority") or "").strip(),
        "CSV publish_date": (row.get("publish_date") or "").strip(),
        "CSV effective_date": (row.get("effective_date") or "").strip(),
        "PDF path": pdf_path,
        "PDF SHA-256": sha,
        "PDF 首页原文标题": first_lines,
        "PDF 发布机关": publisher,
        "PDF 版本/生效日期": version,
        "当前绑定结论": diagnosis,
        "建议处置": disposition,
        "专家意见": "",
        "审核人": "",
        "审核日期": "",
    }


def _row_for_orphan(sid: str, relpath: str) -> dict[str, str]:
    p = (ROOT / relpath).resolve()
    sha = ""
    text = ""
    if p.exists():
        sha = _sha256(p)
        text = _extract_first_page_text(p)
    diagnosis, disposition = ADJUDICATION_DRAFT.get(sid, ("", ""))
    return {
        "source_id": sid,
        "CSV title": "",
        "CSV doc_type": "",
        "CSV authority": "",
        "CSV publish_date": "",
        "CSV effective_date": "",
        "PDF path": relpath,
        "PDF SHA-256": sha,
        "PDF 首页原文标题": _first_lines(text),
        "PDF 发布机关": _detect_publisher(text, p.name) if p.exists() else "",
        "PDF 版本/生效日期": _extract_version_from_filename(p.name) if p.exists() else "",
        "当前绑定结论": diagnosis,
        "建议处置": disposition,
        "专家意见": "",
        "审核人": "",
        "审核日期": "",
    }


def build_rows() -> list[dict[str, str]]:
    source_rows = _load_csv_rows()
    rows: list[dict[str, str]] = []
    for sid in QUARANTINED_SOURCE_IDS:
        rows.append(_row_for_source(sid, source_rows.get(sid, {})))
    for sid in REVIEW_ONLY_SOURCE_IDS:
        rows.append(_row_for_source(sid, source_rows.get(sid, {})))
    for sid, relpath in ORPHAN_PDFS.items():
        rows.append(_row_for_orphan(sid, relpath))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write the draft CSV (preserving human sign-off columns)")
    ap.add_argument("--check", action="store_true", help="fail if the CSV is missing or structurally invalid")
    args = ap.parse_args()

    rows = build_rows()
    human = _load_existing_human_signoff()
    for row in rows:
        prior = human.get(row["source_id"], {})
        for col in HUMAN_COLUMNS:
            row[col] = prior.get(col, "")

    if args.check:
        if not OUT_CSV.exists():
            print(f"FAIL adjudication CSV missing: {OUT_CSV.relative_to(ROOT)}")
            return 2
        if not _load_existing_human_signoff():
            print("FAIL adjudication CSV has no rows")
            return 2
        for row in rows:
            if row["建议处置"] and row["建议处置"] not in LEGAL_DISPOSITIONS:
                print(f"FAIL illegal disposition {row['建议处置']!r} for {row['source_id']}")
                return 2
        print(f"OK   adjudication CSV present with {len(rows)} draft rows (human sign-off preserved)")
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
