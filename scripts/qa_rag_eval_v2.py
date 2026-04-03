#!/usr/bin/env python3
"""RAG evaluation v2: larger benchmark with source-level gold labels and robust metrics."""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common.rag.retriever import RegulationDoc, retrieve_regulations

DATASET_CSV = ROOT / "doc/knowledge/evaluation/rag_eval_v2_queries.csv"
SOURCES_CSV = ROOT / "doc/knowledge/index/sources.csv"
OUT_JSON = ROOT / "qa/rag_eval_v2.json"
OUT_MD = ROOT / "doc/v2/qa-rag-v2.md"

EVAL_MODES: tuple[str, ...] = ("vector", "hybrid")


@dataclass
class QueryRow:
    query_id: str
    module: str
    split: str
    difficulty: str
    label_type: str
    query: str
    gold_source_ids: tuple[str, ...]
    expected_jurisdiction: str
    expected_path: str
    expected_empty: bool


def _extract_source_id(article_id: str) -> str:
    m = re.match(r"^([A-Z]{2}-[A-Z]+-\d{3})", article_id)
    return m.group(1) if m else article_id


def _split_pipe(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (value or "").split("|") if part.strip())


def _is_valid_citation(doc: RegulationDoc) -> bool:
    if not doc.source_url.strip() or not doc.snapshot_path.strip():
        return False
    snapshot = ROOT / doc.snapshot_path
    return snapshot.exists()


def _load_source_titles() -> dict[str, str]:
    table: dict[str, str] = {}
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as fp:
        for row in csv.DictReader(fp):
            sid = (row.get("source_id") or "").strip()
            title = (row.get("title") or "").strip()
            if sid:
                table[sid] = title
    return table


def _load_rows() -> list[QueryRow]:
    if not DATASET_CSV.exists():
        raise FileNotFoundError(f"missing dataset: {DATASET_CSV}")

    rows: list[QueryRow] = []
    with DATASET_CSV.open("r", encoding="utf-8", newline="") as fp:
        for row in csv.DictReader(fp):
            rows.append(
                QueryRow(
                    query_id=row["query_id"],
                    module=row["module"],
                    split=row["split"],
                    difficulty=row["difficulty"],
                    label_type=row["label_type"],
                    query=row["query"],
                    gold_source_ids=_split_pipe(row.get("gold_source_ids", "")),
                    expected_jurisdiction=row.get("expected_jurisdiction", ""),
                    expected_path=row.get("expected_path", ""),
                    expected_empty=(row.get("expected_empty", "no").strip().lower() == "yes"),
                )
            )
    return rows


def _dcg_binary(relevant_positions: list[int], top_k: int) -> float:
    dcg = 0.0
    for pos in relevant_positions:
        if pos > top_k:
            continue
        dcg += 1.0 / math.log2(pos + 1)
    return dcg


def _idcg_binary(relevant_total: int, top_k: int) -> float:
    r = min(relevant_total, top_k)
    if r <= 0:
        return 0.0
    return sum(1.0 / math.log2(i + 1) for i in range(1, r + 1))


def run_eval(top_k: int = 5, mode: str = "hybrid") -> dict:
    rows = _load_rows()
    source_titles = _load_source_titles()

    details: list[dict] = []

    # positive aggregates
    pos_total = 0
    pos_hit = 0
    pos_top1 = 0
    pos_precision_sum = 0.0
    pos_mrr_sum = 0.0
    pos_ndcg_sum = 0.0
    pos_cit_top1 = 0
    pos_cit_ratio_sum = 0.0
    pos_title_leak = 0

    # negative aggregates
    neg_total = 0
    neg_safe_reject = 0

    by_module: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_split: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_difficulty: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for row in rows:
        hits = retrieve_regulations(
            query=row.query,
            top_k=top_k,
            jurisdiction=row.expected_jurisdiction,
            path=row.expected_path,
            mode=mode,
        )

        hit_sources = [_extract_source_id(doc.id) for doc in hits]

        if row.label_type == "positive":
            pos_total += 1
            gold = set(row.gold_source_ids)

            # For ranking metrics, de-duplicate by source_id to avoid counting
            # repeated chunks from the same source as multiple relevant hits.
            rel_positions: list[int] = []
            seen_rel_sources: set[str] = set()
            for idx, sid in enumerate(hit_sources):
                if sid in gold and sid not in seen_rel_sources:
                    rel_positions.append(idx + 1)
                    seen_rel_sources.add(sid)
            hit_at_k = len(rel_positions) > 0
            top1_ok = len(hit_sources) > 0 and hit_sources[0] in gold

            if hit_at_k:
                pos_hit += 1
            if top1_ok:
                pos_top1 += 1

            rel_count = sum(1 for sid in hit_sources[:top_k] if sid in gold)
            precision_k = rel_count / top_k if top_k else 0.0
            pos_precision_sum += precision_k

            mrr = 1.0 / rel_positions[0] if rel_positions else 0.0
            pos_mrr_sum += mrr

            dcg = _dcg_binary(rel_positions, top_k=top_k)
            idcg = _idcg_binary(relevant_total=max(len(gold), 1), top_k=top_k)
            ndcg = dcg / idcg if idcg > 0 else 0.0
            pos_ndcg_sum += ndcg

            cit_top1 = _is_valid_citation(hits[0]) if hits else False
            if cit_top1:
                pos_cit_top1 += 1

            cit_valid = sum(1 for doc in hits[:top_k] if _is_valid_citation(doc))
            cit_ratio = cit_valid / top_k if top_k else 0.0
            pos_cit_ratio_sum += cit_ratio

            # explicit leakage: query includes full title string of any gold source
            q_norm = row.query.lower()
            has_title_leak = False
            for sid in gold:
                title = source_titles.get(sid, "").strip().lower()
                if title and title in q_norm:
                    has_title_leak = True
                    break
            if has_title_leak:
                pos_title_leak += 1

            by_module[row.module]["pos_total"] += 1
            by_module[row.module]["pos_hit"] += 1 if hit_at_k else 0
            by_module[row.module]["pos_top1"] += 1 if top1_ok else 0
            by_module[row.module]["pos_mrr_sum"] += mrr
            by_module[row.module]["pos_precision_sum"] += precision_k

            by_split[row.split]["pos_total"] += 1
            by_split[row.split]["pos_hit"] += 1 if hit_at_k else 0

            by_difficulty[row.difficulty]["pos_total"] += 1
            by_difficulty[row.difficulty]["pos_hit"] += 1 if hit_at_k else 0

            details.append(
                {
                    "query_id": row.query_id,
                    "module": row.module,
                    "split": row.split,
                    "difficulty": row.difficulty,
                    "label_type": row.label_type,
                    "query": row.query,
                    "gold_source_ids": sorted(gold),
                    "hit_sources": hit_sources,
                    "hit": hit_at_k,
                    "top1_correct": top1_ok,
                    "precision_at_k": precision_k,
                    "mrr": mrr,
                    "ndcg_at_k": ndcg,
                    "top_titles": [f"{doc.title}{doc.article}" for doc in hits],
                }
            )

        else:
            neg_total += 1
            safe_reject = len(hits) == 0 if row.expected_empty else True
            if safe_reject:
                neg_safe_reject += 1

            by_module[row.module]["neg_total"] += 1
            by_module[row.module]["neg_safe_reject"] += 1 if safe_reject else 0

            by_split[row.split]["neg_total"] += 1
            by_split[row.split]["neg_safe_reject"] += 1 if safe_reject else 0

            details.append(
                {
                    "query_id": row.query_id,
                    "module": row.module,
                    "split": row.split,
                    "difficulty": row.difficulty,
                    "label_type": row.label_type,
                    "query": row.query,
                    "expected_empty": row.expected_empty,
                    "safe_reject": safe_reject,
                    "hit_sources": hit_sources,
                    "top_titles": [f"{doc.title}{doc.article}" for doc in hits],
                }
            )

    module_stats: dict[str, dict[str, float]] = {}
    for module, acc in by_module.items():
        pt = int(acc.get("pos_total", 0))
        nt = int(acc.get("neg_total", 0))
        module_stats[module] = {
            "positive_queries": pt,
            "positive_recall_at_k": (acc.get("pos_hit", 0.0) / pt) if pt else 0.0,
            "positive_top1_acc": (acc.get("pos_top1", 0.0) / pt) if pt else 0.0,
            "positive_mrr": (acc.get("pos_mrr_sum", 0.0) / pt) if pt else 0.0,
            "positive_precision_at_k": (acc.get("pos_precision_sum", 0.0) / pt) if pt else 0.0,
            "negative_queries": nt,
            "negative_safe_reject_rate": (acc.get("neg_safe_reject", 0.0) / nt) if nt else 0.0,
        }

    split_stats: dict[str, dict[str, float]] = {}
    for split, acc in by_split.items():
        pt = int(acc.get("pos_total", 0))
        nt = int(acc.get("neg_total", 0))
        split_stats[split] = {
            "positive_queries": pt,
            "positive_recall_at_k": (acc.get("pos_hit", 0.0) / pt) if pt else 0.0,
            "negative_queries": nt,
            "negative_safe_reject_rate": (acc.get("neg_safe_reject", 0.0) / nt) if nt else 0.0,
        }

    difficulty_stats: dict[str, dict[str, float]] = {}
    for diff, acc in by_difficulty.items():
        pt = int(acc.get("pos_total", 0))
        difficulty_stats[diff] = {
            "positive_queries": pt,
            "positive_recall_at_k": (acc.get("pos_hit", 0.0) / pt) if pt else 0.0,
        }

    summary = {
        "positive_queries": pos_total,
        "positive_recall_at_k": (pos_hit / pos_total) if pos_total else 0.0,
        "positive_top1_acc": (pos_top1 / pos_total) if pos_total else 0.0,
        "positive_precision_at_k": (pos_precision_sum / pos_total) if pos_total else 0.0,
        "positive_mrr": (pos_mrr_sum / pos_total) if pos_total else 0.0,
        "positive_ndcg_at_k": (pos_ndcg_sum / pos_total) if pos_total else 0.0,
        "positive_top1_citation_valid_rate": (pos_cit_top1 / pos_total) if pos_total else 0.0,
        "positive_avg_citation_valid_ratio": (pos_cit_ratio_sum / pos_total) if pos_total else 0.0,
        "positive_title_leak_rate": (pos_title_leak / pos_total) if pos_total else 0.0,
        "negative_queries": neg_total,
        "negative_safe_reject_rate": (neg_safe_reject / neg_total) if neg_total else 0.0,
    }

    return {
        "mode": mode,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(DATASET_CSV.relative_to(ROOT)),
        "top_k": top_k,
        "summary": summary,
        "module_stats": module_stats,
        "split_stats": split_stats,
        "difficulty_stats": difficulty_stats,
        "details": details,
    }


def run_compare(top_k: int = 5) -> dict:
    mode_reports = {mode: run_eval(top_k=top_k, mode=mode) for mode in EVAL_MODES}
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "top_k": top_k,
        "dataset": str(DATASET_CSV.relative_to(ROOT)),
        "modes": mode_reports,
    }


def _render_md(report: dict) -> str:
    lines: list[str] = []
    lines.append("# RAG 评测（v2，增强版）")
    lines.append("")
    lines.append(f"生成时间：{report['generated_at']}")
    lines.append(f"数据集：`{report['dataset']}`")
    lines.append(f"Top-K：{report['top_k']}")
    lines.append("")

    lines.append("## 总体对比")
    lines.append("")
    lines.append("| 模式 | 正例数 | Recall@K | Top1 Acc | Precision@K | MRR | nDCG@K | 负例数 | SafeReject | 标题泄漏率 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for mode in EVAL_MODES:
        s = report["modes"][mode]["summary"]
        lines.append(
            f"| {mode} | {s['positive_queries']} | {s['positive_recall_at_k']:.3f} | {s['positive_top1_acc']:.3f} | {s['positive_precision_at_k']:.3f} | {s['positive_mrr']:.3f} | {s['positive_ndcg_at_k']:.3f} | {s['negative_queries']} | {s['negative_safe_reject_rate']:.3f} | {s['positive_title_leak_rate']:.3f} |"
        )
    lines.append("")

    for mode in EVAL_MODES:
        lines.append(f"## 分模块（{mode}）")
        lines.append("")
        lines.append("| 模块 | 正例数 | Recall@K | Top1 | MRR | 负例数 | SafeReject |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for module in sorted(report["modes"][mode]["module_stats"].keys()):
            m = report["modes"][mode]["module_stats"][module]
            lines.append(
                f"| {module} | {int(m['positive_queries'])} | {m['positive_recall_at_k']:.3f} | {m['positive_top1_acc']:.3f} | {m['positive_mrr']:.3f} | {int(m['negative_queries'])} | {m['negative_safe_reject_rate']:.3f} |"
            )
        lines.append("")

        bad_pos = [d for d in report["modes"][mode]["details"] if d["label_type"] == "positive" and not d["hit"]]
        bad_neg = [d for d in report["modes"][mode]["details"] if d["label_type"] == "negative" and not d["safe_reject"]]

        lines.append(f"### 正例未命中样例（前10，{mode}）")
        lines.append("")
        if not bad_pos:
            lines.append("- 无")
        else:
            for row in bad_pos[:10]:
                lines.append(
                    f"- `{row['query_id']}` `{row['module']}`: {row['query']} | top: {', '.join(row['top_titles'][:2])}"
                )
        lines.append("")

        lines.append(f"### 负例未拒绝样例（前10，{mode}）")
        lines.append("")
        if not bad_neg:
            lines.append("- 无")
        else:
            for row in bad_neg[:10]:
                lines.append(
                    f"- `{row['query_id']}` `{row['module']}`: {row['query']} | top: {', '.join(row['top_titles'][:2])}"
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    report = run_compare(top_k=5)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(_render_md(report), encoding="utf-8")

    print(f"json: {OUT_JSON}")
    print(f"md: {OUT_MD}")
    print(
        "summary:",
        {
            mode: {
                "pos": report["modes"][mode]["summary"]["positive_queries"],
                "recall": round(report["modes"][mode]["summary"]["positive_recall_at_k"], 3),
                "top1": round(report["modes"][mode]["summary"]["positive_top1_acc"], 3),
                "mrr": round(report["modes"][mode]["summary"]["positive_mrr"], 3),
                "neg_safe_reject": round(report["modes"][mode]["summary"]["negative_safe_reject_rate"], 3),
            }
            for mode in EVAL_MODES
        },
    )


if __name__ == "__main__":
    main()
