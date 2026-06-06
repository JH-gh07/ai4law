#!/usr/bin/env python3
"""ai4law Module Quality Evaluation Runner (offline / disk-scan mode).

Scans outputs/{module}/ for the most recent run, reads citation_map.json,
trace data, and output files directly from disk, then runs three audit checkers.

Usage:
    python scripts/eval_runner.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys_path_str = str(PROJECT_ROOT)
if sys_path_str not in os.environ.get("PYTHONPATH", ""):
    import sys
    sys.path.insert(0, sys_path_str)

from scripts.eval_checkers.citations import check_citations
from scripts.eval_checkers.conclusions import check_conclusions
from scripts.eval_checkers.report import generate_module_summary, generate_index

DATE_STAMP = datetime.now().strftime("%Y-%m-%d")
OUTPUT_BASE = PROJECT_ROOT / "outputs" / "evaluations" / DATE_STAMP
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"

# Module name → expected output directory name
MODULES = [
    "assessment", "pipia", "scc", "review", "eu_scc",
    "bcr", "dpia", "tia", "cn_flow", "us_14117", "cpra",
    "diagnosis",
]


def _pick_latest_run(module: str) -> Path | None:
    """Find the most recent run directory for a module."""
    mod_dir = OUTPUTS_ROOT / module
    if not mod_dir.is_dir():
        return None
    dirs = [d for d in mod_dir.iterdir() if d.is_dir() and not d.name.startswith("_")
            and not d.name.startswith(".") and (d / "outputs").exists()]
    if not dirs:
        return None
    # Pick newest by mtime
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return dirs[0]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _list_output_files(outputs_dir: Path) -> dict[str, dict[str, Any]]:
    """List all files in output directory with size."""
    result = {}
    if not outputs_dir.is_dir():
        return result
    for f in sorted(outputs_dir.iterdir()):
        if f.is_file():
            result[f.name] = {
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "non_empty": f.stat().st_size > 50,
            }
    return result


def run_one_module(module: str, label: str) -> dict[str, Any]:
    """Run audit for one module using disk data."""
    run_dir = _pick_latest_run(module)
    if not run_dir:
        return generate_module_summary(
            module, label, "", {}, {}, {}, "no_data", 0,
            f"No output directory found for {module}"
        )

    task_id = run_dir.name
    outputs_dir = run_dir / "outputs"

    # ── Citation audit ──
    citation_map_path = outputs_dir / "citation_map.json"
    citation_audit = check_citations_from_disk(citation_map_path, module)

    # ── Execution flow audit ──
    trace_dir = run_dir if (run_dir / "trace").is_dir() else None
    exec_audit = check_execution_flow_from_disk(run_dir, module)

    # ── Conclusion audit ──
    output_files = _list_output_files(outputs_dir)
    conc_audit = check_conclusions_from_disk(output_files, module)

    # ── Save ──
    case_dir = OUTPUT_BASE / module
    case_dir.mkdir(parents=True, exist_ok=True)
    _write_json(case_dir / "citation_audit.json", citation_audit)
    _write_json(case_dir / "trace_audit.json", exec_audit)
    _write_json(case_dir / "conclusion_audit.json", conc_audit)
    _write_json(case_dir / "output_files.json", output_files)

    return generate_module_summary(
        module, label, task_id,
        citation_audit, exec_audit, conc_audit,
        "completed", 0, "",
    )


def check_citations_from_disk(citation_map_path: Path, module: str) -> dict:
    if not citation_map_path.is_file():
        return {
            "task_id": "", "module": module,
            "citation_map_exists": False, "citation_count": 0,
            "citations": [], "score": 0,
            "issues": ["citation_map.json not found on disk"],
            "summary": "No citation map — citations not clickable",
        }
    data = _read_json(citation_map_path)
    footnote_map = data.get("footnote_map", {})
    all_items = data.get("all_items", []) or list(footnote_map.values())

    score_total = 0
    citations = []
    for i, item in enumerate(all_items):
        cit = {
            "index": i + 1,
            "title": item.get("title", ""),
            "article_no": item.get("article_no", ""),
            "has_knowledge_url": bool(item.get("knowledge_url")),
            "knowledge_url": item.get("knowledge_url", ""),
            "has_quote_text": bool(item.get("quote_text")),
            "has_authority_level": bool(item.get("authority_level")),
            "has_confidence_score": bool(item.get("confidence_score", 0) > 0),
            "score": 0,
        }
        if cit["has_knowledge_url"]:
            cit["score"] += 5
        if cit["has_quote_text"]:
            cit["score"] += 5
        if cit["has_authority_level"]:
            cit["score"] += 5
        if cit["has_confidence_score"]:
            cit["score"] += 5
        if item.get("source_id"):
            cit["score"] += 5
        citations.append(cit)
        score_total += cit["score"]

    max_p = len(all_items) * 25
    score = round((score_total / max_p * 100), 1) if max_p > 0 else 50

    issues = [] if len(all_items) > 0 else ["Empty citation map"]
    if len(all_items) > 0 and not any(c.get("has_knowledge_url") for c in citations):
        issues.append("No citations have knowledge_url — not clickable")

    return {
        "task_id": "", "module": module,
        "citation_map_exists": len(all_items) > 0,
        "citation_count": len(all_items),
        "citations": citations,
        "score": min(score, 100),
        "issues": issues,
        "summary": f"{len(all_items)} citations, {'clickable' if score >= 50 else 'not clickable'}: {score}%",
    }


def check_execution_flow_from_disk(run_dir: Path, module: str) -> dict:
    """Check trace events from trace directory or trace_manifest.json."""
    trace_dir = run_dir / "trace"
    manifest_path = run_dir / "outputs" / "trace_manifest.json"

    # Count trace files
    event_count = 0
    event_types = set()
    has_token = False
    token_stages = []

    if trace_dir.is_dir():
        for f in sorted(trace_dir.iterdir()):
            if f.suffix == ".json" and f.name != "manifest.json":
                event_count += 1
                data = _read_json(f)
                name = data.get("name", "")
                payload = data.get("payload", {})
                # Map name → event_type
                if "status" in name or "state" in str(payload.get("detail", {})):
                    event_types.add("status")
                elif "thought" in name or "判断" in name:
                    event_types.add("thought")
                elif "tool_start" in name or "agent" in name.lower():
                    event_types.add("tool_start")
                elif "tool_result" in name or "generated" in name:
                    event_types.add("tool_result")
                elif "intermediate" in name or "facts" in name or "issues" in name or "evidence" in name:
                    event_types.add("intermediate")
                elif "warning" in name:
                    event_types.add("warning")
                elif "final" in name:
                    event_types.add("final")
                elif "brief" in name:
                    event_types.add("final_brief")
                elif name not in ("manifest",):
                    event_types.add(name.split("_")[0] if "_" in name else name)

                # Check for token data
                if payload.get("token_count") or payload.get("token_usage"):
                    has_token = True
    elif manifest_path.is_file():
        data = _read_json(manifest_path)
        events = data.get("events", [])
        event_count = len(events)
        for e in events:
            name = e.get("step", e.get("name", ""))
            if "diagnosis" in name or "path" in name:
                event_types.add("thought")
            elif "fact" in name:
                event_types.add("tool_start")
            elif "retrieval" in name or "rag" in name:
                event_types.add("tool_start")
            elif "issue" in name or "evidence" in name:
                event_types.add("intermediate")
            elif "chapter" in name or "generat" in name or "render" in name:
                event_types.add("tool_result")
            elif "consistency" in name:
                event_types.add("tool_result")

    missing = {"status", "thought", "tool_start", "tool_result", "intermediate", "warning", "final", "final_brief"} - event_types
    coverage = round(len(event_types) / 8 * 100, 1)
    score = round(coverage * 0.5 + (50 if has_token else 0), 1)

    return {
        "task_id": "", "module": module,
        "total_events": event_count,
        "event_types_found": sorted(event_types),
        "event_types_missing": sorted(missing),
        "type_coverage_pct": coverage,
        "has_token_data": has_token,
        "token_by_stage": token_stages,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "score": score,
        "issues": [] if event_count > 0 else ["No trace events found"],
        "summary": f"{event_count} trace events, {len(event_types)}/8 event types, token data: {'YES' if has_token else 'NO'}: {score}%",
    }


def check_conclusions_from_disk(output_files: dict, module: str) -> dict:
    """Check output files on disk."""
    expected_sets = {
        "assessment": {"docx", "md", "pdf", "xlsx", "zip", "json"},
        "cpra": {"docx", "md", "pdf", "xlsx", "zip"},
        "pipia": {"docx", "zip"},
        "bcr": {"docx", "zip"},
        "dpia": {"docx", "md", "zip", "json"},
        "tia": {"docx", "zip"},
        "scc": {"docx", "zip"},
        "eu_scc": {"docx", "zip"},
        "us_14117": {"docx", "md", "zip"},
        "cn_flow": {"xlsx", "zip"},
        "review": {"docx", "zip"},
        "diagnosis": {"html", "pdf"},
    }
    expected = expected_sets.get(module, {"docx", "zip"})

    total = len(output_files)
    existing = sum(1 for v in output_files.values() if v["non_empty"])
    report_ok = any(k in output_files and output_files[k]["non_empty"]
                    for k in ("report.md", "markdown", "*.md", "docx"))
    has_report = any(name.endswith((".md", ".docx", ".pdf", ".html"))
                     and v["non_empty"] for name, v in output_files.items())
    inter_count = sum(1 for name in output_files if ("json" in name or "xlsx" in name)
                      and output_files[name]["non_empty"])

    score = 0
    if total > 0:
        score += 30
    if has_report:
        score += 35
    if inter_count > 0:
        score += 20
    if existing >= 2:
        score += 15

    issues = [] if total > 0 else ["No output files found"]
    if not has_report:
        issues.append("No readable report file (md/docx/pdf/html) found")

    return {
        "task_id": "", "module": module,
        "output_files": {k: v["path"] for k, v in output_files.items()},
        "file_count": total,
        "report_non_empty": has_report,
        "intermediate_file_count": inter_count,
        "score": min(score, 100),
        "issues": issues,
        "summary": f"{total} files, report: {'YES' if has_report else 'NO'}, intermediates: {inter_count}: {score}%",
    }


def _write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  ai4law Module Evaluation (Offline Scan)     ║")
    print(f"║  {DATE_STAMP}                              ║")
    print(f"╚══════════════════════════════════════════════╝")
    print()

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    summaries = []

    for i, module in enumerate(MODULES, 1):
        label = f"{module} (latest run)"
        print(f"[{i}/{len(MODULES)}] {module}")
        summary = run_one_module(module, label)
        summaries.append(summary)
        scores = summary["scores"]
        print(f"  → Citations: {scores['citations']}% | ExecFlow: {scores['execution_flow']}% | Conclusions: {scores['conclusions']}% | Overall: {scores['overall']}%")
        print()

    index = generate_index(DATE_STAMP, summaries, OUTPUT_BASE)
    _write_json(OUTPUT_BASE / "index.json", index)

    print("=" * 70)
    print("FINAL EVALUATION REPORT")
    print(f"Date: {DATE_STAMP}")
    print(f"Modules: {index['total_modules']}")
    print(f"Average Overall: {index['average_overall_score']}%")
    print()
    for dim in ["citations", "execution_flow", "conclusions"]:
        d = index["by_dimension"][dim]
        print(f"  {dim}: avg={d['average']}% | best={d['best']} | worst={d['worst']}")
    print(f"\nFull results: {OUTPUT_BASE}/index.json")


if __name__ == "__main__":
    main()
