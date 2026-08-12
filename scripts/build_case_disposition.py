#!/usr/bin/env python3
"""Build the formal case disposition table (task065 T04).

Reconciles four case surfaces into one machine-checkable table:

  * benchmarks/cases/**/scenario.json  (22 shared scenarios)
  * config/dev_case_catalog.json       (frontend dev cases)
  * config/case_inventory.json         (CLI cases)
  * benchmarks/datasets/seed-cases-v1/inputs/*.input.json  (50 seed extraction records)

Output: status/check/task065/case-disposition.v1.json

The deep business-fact comparison (company/country/counts/recipient/data types/
attachment hash) across Scenario/CLI/frontend is enforced by
scripts/check_case_parity.py; this table records the per-case identity and
classification so that every formal case has exactly one disposition.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_GLOB = "benchmarks/cases/*/*/scenario.json"
DEV_CATALOG = ROOT / "config/dev_case_catalog.json"
INVENTORY = ROOT / "config/case_inventory.json"
SEED_INPUTS = ROOT / "benchmarks/datasets/seed-cases-v1/inputs"
OUT_PATH = ROOT / "status/check/task065/case-disposition.v1.json"

CLASSIFICATIONS = (
    "source_exact",
    "source_derived",
    "product_extension",
    "compatibility_adapter",
    "gap",
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_hash(rel: str | None) -> str | None:
    if not rel:
        return None
    p = ROOT / rel
    return sha256_of(p) if p.exists() else None


def collect_scenarios() -> list[dict]:
    out = []
    for sp in sorted(ROOT.glob(SCENARIO_GLOB)):
        d = json.loads(sp.read_text(encoding="utf-8"))
        src = d.get("source", {})
        source_file = src.get("file", "")
        out.append(
            {
                "case_id": d.get("case_id"),
                "module": d.get("module"),
                "classification": d.get("classification"),
                "jurisdiction": d.get("display", {}).get("jurisdiction"),
                "display_name": d.get("display", {}).get("name"),
                "source_file": source_file,
                "source_case": src.get("case"),
                "source_sha256": safe_hash(source_file),
                "expected_path": f"{sp.parent.name}/expected.json"
                if (sp.parent / "expected.json").exists()
                else None,
                "surface": "scenario",
            }
        )
    return out


def collect_frontend() -> list[dict]:
    d = json.loads(DEV_CATALOG.read_text(encoding="utf-8"))
    out = []
    for c in d.get("cases", []):
        out.append(
            {
                "case_id": c.get("case_id"),
                "module": c.get("module"),
                "classification": c.get("classification"),
                "jurisdiction": None,
                "display_name": c.get("source_case"),
                "source_file": c.get("source_file"),
                "source_case": c.get("source_case"),
                "source_sha256": safe_hash(c.get("source_file")),
                "expected_path": None,
                "surface": "frontend",
            }
        )
    return out


def collect_cli() -> list[dict]:
    d = json.loads(INVENTORY.read_text(encoding="utf-8"))
    out = []
    for mod, meta in d.get("modules", {}).items():
        for cc in meta.get("cli_cases", []):
            out.append(
                {
                    "case_id": f"{mod}-{cc['case_id']}",
                    "module": mod,
                    "classification": None,  # CLI cases inherit from scenario
                    "jurisdiction": None,
                    "display_name": None,
                    "source_file": None,
                    "source_case": None,
                    "source_sha256": None,
                    "expected_path": None,
                    "surface": "cli",
                }
            )
    return out


def collect_seed() -> list[dict]:
    out = []
    for ip in sorted(SEED_INPUTS.glob("*.input.json")):
        d = json.loads(ip.read_text(encoding="utf-8"))
        mapping_status = d.get("mapping_status")
        classification = "gap" if mapping_status == "gap" else None
        out.append(
            {
                "case_id": d.get("case_id"),
                "module": d.get("module_id") or None,
                "classification": classification,
                "jurisdiction": d.get("jurisdiction"),
                "display_name": d.get("declared_task_name"),
                "source_file": d.get("source_docx"),
                "source_case": None,
                "source_sha256": d.get("source_sha256"),
                "expected_path": None,
                "surface": "seed",
                "mapping_status": mapping_status,
            }
        )
    return out


def main() -> int:
    scenarios = collect_scenarios()
    frontend = collect_frontend()
    cli = collect_cli()
    seed = collect_seed()

    # Validate classification enum on scenarios and frontend.
    errors = []
    for rec in scenarios + frontend:
        if rec["classification"] not in CLASSIFICATIONS:
            errors.append(
                f"{rec['surface']} {rec['case_id']}: bad classification "
                f"{rec['classification']!r}"
            )

    # Every seed case must have a mapping_status.
    for rec in seed:
        if rec["mapping_status"] not in ("partial", "gap"):
            errors.append(f"seed {rec['case_id']}: bad mapping_status {rec['mapping_status']!r}")

    out = {
        "schema_version": "1.0",
        "generated_by": "scripts/build_case_disposition.py",
        "date": "2026-08-13",
        "classifications": list(CLASSIFICATIONS),
        "counts": {
            "scenarios": len(scenarios),
            "frontend": len(frontend),
            "cli": len(cli),
            "seed": len(seed),
        },
        "scenarios": scenarios,
        "frontend_cases": frontend,
        "cli_cases": cli,
        "seed_cases": seed,
        "validation_errors": errors,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"scenarios  : {len(scenarios)}")
    print(f"frontend   : {len(frontend)}")
    print(f"cli        : {len(cli)}")
    print(f"seed       : {len(seed)}")
    print(f"validation errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"WROTE {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
