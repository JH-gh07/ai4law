"""Conclusion dimension checker — evaluates report quality, file downloadability, and completeness."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any


def check_conclusions(
    task_id: str,
    module: str,
    result: dict[str, Any],
    project_root: str | None = None,
) -> dict[str, Any]:
    """Run conclusion audit for one task run.

    Checks: output_files completeness, file existence on disk, report content presence.
    """
    if project_root is None:
        project_root = str(Path(__file__).resolve().parents[2])

    findings: dict[str, Any] = {
        "task_id": task_id,
        "module": module,
        "output_files": {},
        "files_on_disk": {},
        "report_non_empty": False,
        "intermediates_exist": False,
        "score": 0,
        "issues": [],
        "summary": "",
    }

    # ── 1. Expected output files per module ──
    expected = _expected_files(module)

    # ── 2. Check output_files dict from API response ──
    output_files = result.get("output_files", {}) or {}
    findings["output_files"] = {
        key: {"path": val, "expected": key in expected}
        for key, val in output_files.items()
    }

    generated_count = len(output_files)
    findings["generated_file_count"] = generated_count

    if generated_count == 0:
        findings["issues"].append("No output files listed in API response")
        findings["summary"] = "No output files generated"
        findings["score"] = 0
        return findings

    # ── 3. Check files exist on disk ──
    disk_found = {}
    for key, path in output_files.items():
        full_path = os.path.join(project_root, path) if not os.path.isabs(path) else path
        exists = os.path.isfile(full_path)
        size = os.path.getsize(full_path) if exists else 0
        disk_found[key] = {
            "path": path,
            "exists": exists,
            "size_bytes": size,
            "non_empty": size > 100 if exists else False,
        }

    findings["files_on_disk"] = disk_found

    # ── 4. Report content check ──
    for report_key in ("markdown", "md", "docx", "report"):
        if report_key in disk_found and disk_found[report_key]["non_empty"]:
            findings["report_non_empty"] = True
            break

    # ── 5. Intermediates check ──
    inter_keys = {"facts", "issues", "evidence", "gap_items", "risk_matrix"}
    inter_count = 0
    for key in output_files:
        if key in inter_keys or "_json" in key or "_list" in key:
            if disk_found.get(key, {}).get("non_empty"):
                inter_count += 1
    findings["intermediates_exist"] = inter_count > 0
    findings["intermediate_file_count"] = inter_count

    # ── 6. Scoring ──
    score = 0
    # 35 pts: output files listed
    file_ratio = min(generated_count / max(len(expected), 1), 1.0)
    score += file_ratio * 35
    # 35 pts: files exist on disk and are non-empty
    if disk_found:
        disk_ok = sum(1 for v in disk_found.values() if v["exists"] and v["non_empty"])
        disk_ratio = disk_ok / max(len(disk_found), 1)
        score += disk_ratio * 35
    # 15 pts: report non-empty
    if findings["report_non_empty"]:
        score += 15
    # 15 pts: intermediates exist
    if findings["intermediates_exist"]:
        score += 15

    findings["score"] = round(score, 1)

    if findings["score"] >= 80:
        findings["summary"] = f"Conclusions & files fully valid: {findings['score']}%"
    elif findings["score"] >= 40:
        findings["summary"] = f"Conclusions & files partially valid: {findings['score']}% — some files missing or empty"
    else:
        findings["summary"] = f"Conclusions & files severely deficient: {findings['score']}%"

    for k, v in disk_found.items():
        if not v["exists"]:
            findings["issues"].append(f"File missing on disk: {v['path']}")
        elif not v["non_empty"]:
            findings["issues"].append(f"File empty or too small: {v['path']} ({v['size_bytes']} bytes)")

    return findings


def _expected_files(module: str) -> set[str]:
    """Return the set of expected output file keys for a module."""
    base = {"docx", "markdown", "md", "pdf", "xlsx", "zip"}
    inter = {
        "assessment": {"facts_json", "issue_list_json", "evidence_chain_json", "material_checklist_json"},
        "cpra": {"xlsx"},  # CPRA mainly produces docx/md/pdf/xlsx/zip
        "dpia": {"evidence_chain_json", "issue_list_json"},
        "pipia": {"docx", "zip"},
        "bcr": {"docx", "zip"},
        "tia": {"docx", "zip"},
        "eu_scc": {"docx", "zip"},
        "scc": {"docx", "zip"},
        "us_14117": {"docx", "zip"},
        "cn_flow": {"docx", "zip"},
        "review": {"docx", "zip"},
        "diagnosis": {"html", "pdf"},
    }
    return base | inter.get(module, set())
