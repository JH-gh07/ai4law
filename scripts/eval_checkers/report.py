"""Summary report generator — merges citation, execution flow, and conclusion audits into per-module JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_module_summary(
    module_key: str,
    case_label: str,
    task_id: str,
    citation_audit: dict[str, Any],
    execution_flow_audit: dict[str, Any],
    conclusion_audit: dict[str, Any],
    status: str,  # "completed" | "failed" | "timeout" | "network_error"
    duration_seconds: float,
    error_detail: str = "",
) -> dict[str, Any]:
    """Generate a per-module summary dict."""
    return {
        "module": module_key,
        "case_label": case_label,
        "task_id": task_id,
        "status": status,
        "duration_seconds": round(duration_seconds, 1),
        "error_detail": error_detail,
        "scores": {
            "citations": citation_audit.get("score", 0),
            "execution_flow": execution_flow_audit.get("score", 0),
            "conclusions": conclusion_audit.get("score", 0),
            "overall": round(
                (citation_audit.get("score", 0)
                 + execution_flow_audit.get("score", 0)
                 + conclusion_audit.get("score", 0))
                / 3,
                1,
            ),
        },
        "summaries": {
            "citations": citation_audit.get("summary", ""),
            "execution_flow": execution_flow_audit.get("summary", ""),
            "conclusions": conclusion_audit.get("summary", ""),
        },
    }


def generate_index(
    date_stamp: str,
    module_summaries: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    """Generate the master index.json for all modules."""
    completed = [s for s in module_summaries if s["status"] == "completed"]
    failed = [s for s in module_summaries if s["status"] != "completed"]

    overall_scores = [s["scores"]["overall"] for s in completed]
    avg_overall = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0

    return {
        "date": date_stamp,
        "total_modules": len(module_summaries),
        "completed": len(completed),
        "failed": len(failed),
        "average_overall_score": avg_overall,
        "modules": module_summaries,
        "by_dimension": {
            "citations": {
                "average": round(sum(s["scores"]["citations"] for s in completed) / len(completed), 1) if completed else 0,
                "best": max((s for s in completed), key=lambda s: s["scores"]["citations"])["module"] if completed else "N/A",
                "worst": min((s for s in completed), key=lambda s: s["scores"]["citations"])["module"] if completed else "N/A",
            },
            "execution_flow": {
                "average": round(sum(s["scores"]["execution_flow"] for s in completed) / len(completed), 1) if completed else 0,
                "best": max((s for s in completed), key=lambda s: s["scores"]["execution_flow"])["module"] if completed else "N/A",
                "worst": min((s for s in completed), key=lambda s: s["scores"]["execution_flow"])["module"] if completed else "N/A",
            },
            "conclusions": {
                "average": round(sum(s["scores"]["conclusions"] for s in completed) / len(completed), 1) if completed else 0,
                "best": max((s for s in completed), key=lambda s: s["scores"]["conclusions"])["module"] if completed else "N/A",
                "worst": min((s for s in completed), key=lambda s: s["scores"]["conclusions"])["module"] if completed else "N/A",
            },
        },
    }
