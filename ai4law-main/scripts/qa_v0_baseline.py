#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "qa" / "baseline" / "v0_sample_dataset.json"
DEFAULT_BASELINE = ROOT / "qa" / "baseline" / "v0_expected_outputs.json"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "qa"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _poll_completed(client: TestClient, task_id: str, max_attempts: int = 120) -> dict[str, Any]:
    for _ in range(max_attempts):
        resp = client.get(f"/api/v0/tasks/{task_id}")
        resp.raise_for_status()
        data = resp.json()["data"]
        if data["status"] == "COMPLETED":
            return data
        if data["status"] == "FAILED":
            raise RuntimeError(f"Task failed: {task_id} -> {data.get('error')}")
        time.sleep(0.05)
    raise TimeoutError(f"Task timeout: {task_id}")


def _run_case(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    create_resp = client.post(
        "/api/v0/tasks",
        json={
            "module_code": case["module_code"],
            "session_id": f"baseline-{case['name']}",
            "input_payload": case["input_payload"],
            "attachment_ids": case.get("attachment_ids", []),
        },
    )
    create_resp.raise_for_status()
    task_id = create_resp.json()["data"]["task_id"]
    status = _poll_completed(client, task_id)

    artifacts_resp = client.get(f"/api/v0/tasks/{task_id}/artifacts")
    artifacts_resp.raise_for_status()
    artifacts = artifacts_resp.json()["data"]["artifacts"]
    file_types = sorted({item["file_type"] for item in artifacts})
    paths = {item["file_type"]: item["file_path"] for item in artifacts}

    audit_resp = client.get(f"/api/v0/tasks/{task_id}/audit")
    audit_resp.raise_for_status()
    audit = audit_resp.json()["data"]
    rule_hits = audit.get("rule_hits", [])
    if not rule_hits:
        raise RuntimeError(f"No rule_hits in audit for module {case['module_code']}")
    first_rule = rule_hits[0]
    for key in ("rule_id", "hit", "evidence"):
        if key not in first_rule:
            raise RuntimeError(f"rule_hits missing key '{key}' for module {case['module_code']}")

    markdown_sha = ""
    if "markdown" in paths:
        markdown_sha = _sha256_file(Path(paths["markdown"]))

    return {
        "module_code": case["module_code"],
        "name": case["name"],
        "task_id": task_id,
        "status": status["status"],
        "artifact_types": file_types,
        "markdown_sha256": markdown_sha,
        "required_artifacts": sorted(case["required_artifacts"]),
        "audit_rule_hit_count": len(rule_hits),
        "audit_input_digest": audit.get("input_digest", ""),
    }


def _compare_against_baseline(runs: list[dict[str, Any]], baseline: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_map = {item["module_code"]: item for item in baseline.get("cases", [])}
    for run in runs:
        expected = expected_map.get(run["module_code"])
        if expected is None:
            errors.append(f"Missing expected baseline for module {run['module_code']}")
            continue

        missing_types = sorted(set(expected["artifact_types"]) - set(run["artifact_types"]))
        if missing_types:
            errors.append(f"{run['module_code']}: missing artifacts {missing_types}")
        if run["markdown_sha256"] and expected.get("markdown_sha256") != run["markdown_sha256"]:
            errors.append(
                f"{run['module_code']}: markdown sha mismatch expected={expected.get('markdown_sha256')} actual={run['markdown_sha256']}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v0 baseline comparison for all modules.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    baseline_path = Path(args.baseline)
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    client = TestClient(app)

    runs: list[dict[str, Any]] = []
    for case in dataset.get("cases", []):
        run = _run_case(client, case)
        runs.append(run)
        print(
            f"[baseline] module={run['module_code']} artifacts={run['artifact_types']} sha={run['markdown_sha256'][:8]}"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_report = {
        "generated_at": datetime.now().isoformat(),
        "dataset": str(dataset_path),
        "baseline": str(baseline_path),
        "cases": runs,
    }
    run_report_path = output_dir / f"v0_baseline_run_{timestamp}.json"
    run_report_path.write_text(json.dumps(run_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[baseline] run report: {run_report_path}")

    if args.update_baseline:
        baseline_payload = {
            "generated_at": datetime.now().isoformat(),
            "dataset": str(dataset_path),
            "cases": [
                {
                    "module_code": item["module_code"],
                    "name": item["name"],
                    "artifact_types": item["artifact_types"],
                    "markdown_sha256": item["markdown_sha256"],
                }
                for item in runs
            ],
        }
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[baseline] baseline updated: {baseline_path}")
        return 0

    if not baseline_path.exists():
        print(f"[baseline] baseline file not found: {baseline_path}", file=sys.stderr)
        print("[baseline] run with --update-baseline first", file=sys.stderr)
        return 2

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    errors = _compare_against_baseline(runs, baseline)
    if errors:
        print("[baseline] mismatch detected:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print("[baseline] compare passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

