#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOME_FILE = ROOT / "app_streamlit" / "Home.py"
PANEL_FILE = ROOT / "app_streamlit" / "pages" / "0_CN_Service_Panel.py"
REPORT_PREVIEW_FILE = ROOT / "app_streamlit" / "components" / "report_preview.py"
REPORT_CENTER_FILE = ROOT / "app_streamlit" / "pages" / "6_Report_Center.py"
OUTPUT_DIR = ROOT / "outputs" / "qa"


@dataclass
class CheckResult:
    item: str
    passed: bool
    detail: str


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_page_link_targets(py_text: str) -> list[str]:
    targets: list[str] = []
    tree = ast.parse(py_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "page_link" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    targets.append(arg.value)
    return targets


def _extract_cards_list(panel_text: str) -> list[str]:
    tree = ast.parse(panel_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "cards":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        values: list[str] = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Tuple) and elt.elts:
                                first = elt.elts[0]
                                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                                    values.append(first.value)
                        return values
    return []


def run_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    home_text = _read(HOME_FILE)
    panel_text = _read(PANEL_FILE)
    report_preview_text = _read(REPORT_PREVIEW_FILE)
    report_center_text = _read(REPORT_CENTER_FILE)

    home_links = _extract_page_link_targets(home_text)
    expected_home_links = {
        "pages/0_CN_Service_Panel.py",
        "pages/6_Report_Center.py",
        "pages/7_Knowledge_Center.py",
    }
    missing_home = sorted(expected_home_links - set(home_links))
    results.append(
        CheckResult(
            item="home_page_links",
            passed=not missing_home,
            detail="ok" if not missing_home else f"missing: {missing_home}",
        )
    )

    cards = _extract_cards_list(panel_text)
    missing_pages: list[str] = []
    for key in cards:
        page = ROOT / "app_streamlit" / "pages" / f"{key}.py"
        if not page.exists():
            missing_pages.append(str(page))
    results.append(
        CheckResult(
            item="service_panel_cards_to_pages",
            passed=not missing_pages,
            detail="ok" if not missing_pages else f"missing pages: {missing_pages}",
        )
    )

    required_mime_suffixes = [".docx", ".md", ".pdf", ".xlsx", ".zip"]
    missing_suffix_logic = [s for s in required_mime_suffixes if s not in report_preview_text]
    results.append(
        CheckResult(
            item="report_download_mime_support",
            passed=not missing_suffix_logic,
            detail="ok" if not missing_suffix_logic else f"missing suffix logic: {missing_suffix_logic}",
        )
    )

    missing_filter_ext = [s for s in ['".pdf"', '".xlsx"', '".zip"'] if s not in report_center_text]
    results.append(
        CheckResult(
            item="report_center_filter_ext",
            passed=not missing_filter_ext,
            detail="ok" if not missing_filter_ext else f"missing filter ext: {missing_filter_ext}",
        )
    )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check streamlit entry/jump/download linkage.")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = run_checks()
    passed = all(item.passed for item in results)

    report = {
        "passed": passed,
        "checks": [{"item": r.item, "passed": r.passed, "detail": r.detail} for r in results],
    }
    output_path = (
        Path(args.output)
        if args.output
        else OUTPUT_DIR / f"frontend_linkage_check_{Path.cwd().name}.json"
    )
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.item}: {r.detail}")
    print(f"[report] {output_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

