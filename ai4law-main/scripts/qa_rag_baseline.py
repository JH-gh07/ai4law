#!/usr/bin/env python3
"""RAG baseline evaluation for AI4Law knowledge retrieval."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common.rag.retriever import RegulationDoc, retrieve_regulations

PRACTICE_CASES_CSV = ROOT / "doc/knowledge/index/practice_cases.csv"
OUTPUT_MD = ROOT / "doc/v2/qa-rag-v1.md"
OUTPUT_JSON = ROOT / "qa/rag_baseline_v1.json"
EVAL_MODES: tuple[str, ...] = ("vector", "hybrid")

MODULE_FILTERS: dict[str, tuple[str, str]] = {
    "diagnosis": ("cn", "all"),
    "assessment": ("cn", "assessment"),
    "scc": ("cn", "scc"),
    "review": ("cn", "all"),
    "general": ("cn", "all"),
    "bcr": ("eu", "all"),
    "dpia": ("eu", "all"),
    "tia": ("eu", "all"),
    "cn_flow": ("us", "all"),
    "cpra": ("us", "all"),
}


@dataclass
class QueryEval:
    case_id: str
    module: str
    query: str
    hit: bool
    top1_citation_correct: bool
    topk_citation_correct_ratio: float
    top_titles: list[str]


def _split_paths(value: str) -> set[str]:
    return {part.strip() for part in value.split("|") if part.strip()}


def _is_valid_citation(doc: RegulationDoc) -> bool:
    if not doc.source_url.strip() or not doc.snapshot_path.strip():
        return False
    snapshot = ROOT / doc.snapshot_path
    return snapshot.exists()


def _aligns_with_module(doc: RegulationDoc, module: str) -> bool:
    expected = MODULE_FILTERS.get(module)
    if expected is None:
        return False

    expected_jurisdiction, expected_path = expected

    if expected_jurisdiction and doc.jurisdiction and doc.jurisdiction != expected_jurisdiction:
        return False

    if expected_path == "all":
        return True

    doc_paths = _split_paths(doc.path)
    if not doc_paths:
        return False
    return expected_path in doc_paths or "all" in doc_paths


def _load_queries() -> list[tuple[str, str, str]]:
    if not PRACTICE_CASES_CSV.exists():
        raise FileNotFoundError(f"missing practice cases: {PRACTICE_CASES_CSV}")

    queries: list[tuple[str, str, str]] = []
    with PRACTICE_CASES_CSV.open("r", encoding="utf-8", newline="") as fp:
        rows = list(csv.DictReader(fp))

    for row in rows:
        usable = (row.get("usable_for_validation") or "").strip().lower()
        if usable not in {"yes", "partial"}:
            continue

        case_id = row.get("case_id", "")
        case_title = row.get("case_title", "")
        for module in (row.get("expected_module", "") or "").split("|"):
            mod = module.strip()
            if not mod:
                continue
            if mod not in MODULE_FILTERS:
                continue
            queries.append((case_id, mod, case_title))

    return queries


def run_eval(top_k: int = 5, mode: str = "hybrid") -> dict:
    results: list[QueryEval] = []

    total_citation_candidates = 0
    total_valid_citations = 0

    queries = _load_queries()

    for case_id, module, query in queries:
        jurisdiction, path = MODULE_FILTERS[module]
        hits = retrieve_regulations(
            query=query,
            top_k=top_k,
            jurisdiction=jurisdiction,
            path=path,
            mode=mode,
        )

        hit = any(_aligns_with_module(doc, module) for doc in hits)

        top1_citation_correct = _is_valid_citation(hits[0]) if hits else False

        valid_count = 0
        for doc in hits:
            total_citation_candidates += 1
            if _is_valid_citation(doc):
                total_valid_citations += 1
                valid_count += 1

        ratio = (valid_count / len(hits)) if hits else 0.0

        results.append(
            QueryEval(
                case_id=case_id,
                module=module,
                query=query,
                hit=hit,
                top1_citation_correct=top1_citation_correct,
                topk_citation_correct_ratio=ratio,
                top_titles=[f"{doc.title}{doc.article}" for doc in hits],
            )
        )

    total = len(results)
    hit_count = sum(1 for row in results if row.hit)
    top1_ok_count = sum(1 for row in results if row.top1_citation_correct)

    module_stats: dict[str, dict[str, float]] = {}
    grouped: dict[str, list[QueryEval]] = defaultdict(list)
    for row in results:
        grouped[row.module].append(row)

    for module, rows in grouped.items():
        module_total = len(rows)
        module_hits = sum(1 for row in rows if row.hit)
        module_top1 = sum(1 for row in rows if row.top1_citation_correct)
        module_stats[module] = {
            "queries": module_total,
            "recall_at_k": module_hits / module_total if module_total else 0.0,
            "top1_citation_correct_rate": module_top1 / module_total if module_total else 0.0,
            "avg_topk_citation_correct_ratio": sum(row.topk_citation_correct_ratio for row in rows) / module_total
            if module_total
            else 0.0,
        }

    payload = {
        "mode": mode,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "top_k": top_k,
        "summary": {
            "queries": total,
            "recall_at_k": hit_count / total if total else 0.0,
            "top1_citation_correct_rate": top1_ok_count / total if total else 0.0,
            "citation_correct_rate": (total_valid_citations / total_citation_candidates)
            if total_citation_candidates
            else 0.0,
        },
        "module_stats": module_stats,
        "details": [
            {
                "case_id": row.case_id,
                "module": row.module,
                "query": row.query,
                "hit": row.hit,
                "top1_citation_correct": row.top1_citation_correct,
                "topk_citation_correct_ratio": row.topk_citation_correct_ratio,
                "top_titles": row.top_titles,
            }
            for row in results
        ],
    }
    return payload


def run_eval_compare(top_k: int = 5) -> dict:
    mode_reports = {mode: run_eval(top_k=top_k, mode=mode) for mode in EVAL_MODES}
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "top_k": top_k,
        "modes": mode_reports,
    }


def _render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append("# RAG 基线评测（v1）")
    lines.append("")
    lines.append(f"生成时间：{report['generated_at']}")
    lines.append(f"Top-K：{report['top_k']}")
    lines.append("")
    lines.append("## 模式对比（vector vs hybrid）")
    lines.append("")
    lines.append("| 模式 | 查询总数 | Recall@K | Top1引用正确率 | 整体引用正确率 |")
    lines.append("|---|---:|---:|---:|---:|")
    for mode in EVAL_MODES:
        summary = report["modes"][mode]["summary"]
        lines.append(
            f"| {mode} | {summary['queries']} | {summary['recall_at_k']:.3f} | {summary['top1_citation_correct_rate']:.3f} | {summary['citation_correct_rate']:.3f} |"
        )
    lines.append("")

    for mode in EVAL_MODES:
        lines.append(f"## 分模块指标（{mode}）")
        lines.append("")
        lines.append("| 模块 | 查询数 | Recall@K | Top1引用正确率 | 平均TopK引用正确率 |")
        lines.append("|---|---:|---:|---:|---:|")
        for module in sorted(report["modes"][mode]["module_stats"].keys()):
            stat = report["modes"][mode]["module_stats"][module]
            lines.append(
                f"| {module} | {int(stat['queries'])} | {stat['recall_at_k']:.3f} | {stat['top1_citation_correct_rate']:.3f} | {stat['avg_topk_citation_correct_ratio']:.3f} |"
            )
        lines.append("")

        failures = [row for row in report["modes"][mode]["details"] if not row["hit"]]
        lines.append(f"## 未命中样例（前10，{mode}）")
        lines.append("")
        if not failures:
            lines.append("- 无")
        else:
            for row in failures[:10]:
                lines.append(
                    f"- `{row['case_id']}` / `{row['module']}`: {row['query']} | top: {', '.join(row['top_titles'][:3])}"
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    report = run_eval_compare(top_k=5)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(_render_markdown(report), encoding="utf-8")

    print(f"json: {OUTPUT_JSON}")
    print(f"md: {OUTPUT_MD}")
    print(
        "summary:",
        {
            mode: {
                "queries": report["modes"][mode]["summary"]["queries"],
                "recall_at_k": round(report["modes"][mode]["summary"]["recall_at_k"], 3),
                "top1_citation_correct_rate": round(report["modes"][mode]["summary"]["top1_citation_correct_rate"], 3),
                "citation_correct_rate": round(report["modes"][mode]["summary"]["citation_correct_rate"], 3),
            }
            for mode in EVAL_MODES
        },
    )


if __name__ == "__main__":
    main()
