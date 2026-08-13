"""Task067 T10 — headless chromium visual acceptance helper (playwright).

Runs under a Python interpreter that has ``playwright`` installed (the venv
used by ``run_bcr_visual_acceptance.py`` may not). Loads a self-contained
report HTML (same ``report.css`` + faithful block DOM as the React
``ReportDocumentView``) at three real viewports, screenshots each, and records:

- console messages (no uncaught frontend errors allowed)
- network requests (static file render → expected empty)
- layout assertions (no page-level horizontal scroll, no duplicate body,
  expected section / finding / clause counts)

The script is a pure data-in / evidence-out helper: it reads ``--config`` JSON
and writes ``browser_result.json`` + ``*.png`` + console/network logs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _count_duplicates(text: str, anchor: str) -> int:
    return text.count(anchor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="JSON config path")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    html_path = Path(config["html_path"])
    out_dir = Path(config["out_dir"])
    case_id = config["case_id"]
    viewports = config["viewports"]
    expected = config.get("expected", {})
    anchors = config.get("duplicate_anchors", [])

    if not html_path.exists():
        _write_json(out_dir / "browser_result.json", {
            "status": "BLOCKED", "reason": f"missing html {html_path}",
        })
        return 2

    url = html_path.resolve().as_uri()
    console_messages: list[dict] = []
    network_entries: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            locale="zh-CN",
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.on("console", lambda msg: console_messages.append(
            {"type": msg.type, "text": msg.text}
        ))
        page.on("request", lambda req: network_entries.append(
            {"method": req.method, "url": req.url}
        ))
        page.on("response", lambda resp: network_entries.append(
            {"method": resp.request.method, "url": resp.url, "status": resp.status}
        ))

        page.goto(url, wait_until="networkidle")

        screenshots: dict[str, str] = {}
        layout_checks: dict[str, dict] = {}
        for viewport in viewports:
            width, height = viewport["width"], viewport["height"]
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(120)
            screenshot = out_dir / f"{width}_{case_id}_report.png"
            page.screenshot(path=str(screenshot), full_page=False)
            screenshots[f"{width}x{height}"] = str(screenshot.relative_to(out_dir))

            checks = page.evaluate(
                """
                ({ expected, anchors }) => {
                  const docEl = document.documentElement;
                  const bodyText = document.body.innerText || "";
                  const title = document.querySelector(".report-document-header h3");
                  const titleText = title ? title.innerText : "";
                  const result = {
                    horizontal_scroll: docEl.scrollWidth > docEl.clientWidth + 1,
                    scroll_width: docEl.scrollWidth,
                    client_width: docEl.clientWidth,
                    section_count: document.querySelectorAll("section.ir-section").length,
                    finding_card_count: document.querySelectorAll("article.finding-card").length,
                    summary_table_count: document.querySelectorAll("table.ir-summary-table").length,
                    clause_node_count: document.querySelectorAll("li.clause-node").length,
                    citation_note_count: document.querySelectorAll("ol.ir-citation-note li").length,
                    title_text: titleText,
                    duplicate_body: anchors.filter(a => (bodyText.match(new RegExp(a, "g")) || []).length > 1),
                  };
                  return result;
                }
                """,
                {"expected": expected, "anchors": anchors},
            )
            layout_checks[f"{width}x{height}"] = checks

        browser.close()

    console_errors = [m for m in console_messages if m["type"] == "error"]
    # dedupe request+response pairs: keep response entries only
    responses = [e for e in network_entries if "status" in e]

    # aggregate assertions (failures surface here, not as thrown exceptions)
    violations: list[str] = []
    for label, checks in layout_checks.items():
        if checks["horizontal_scroll"]:
            violations.append(f"{label}: page-level horizontal scroll ({checks['scroll_width']}>{checks['client_width']})")
        if checks["duplicate_body"]:
            violations.append(f"{label}: duplicate body anchor {checks['duplicate_body']}")
        if "section_count" in expected and checks["section_count"] != expected["section_count"]:
            violations.append(f"{label}: section_count {checks['section_count']} != {expected['section_count']}")
        if "finding_card_count" in expected and checks["finding_card_count"] != expected["finding_card_count"]:
            violations.append(f"{label}: finding_card_count {checks['finding_card_count']} != {expected['finding_card_count']}")
        if "summary_table_count" in expected and checks["summary_table_count"] != expected["summary_table_count"]:
            violations.append(f"{label}: summary_table_count {checks['summary_table_count']} != {expected['summary_table_count']}")
        if "clause_node_count" in expected and checks["clause_node_count"] != expected["clause_node_count"]:
            violations.append(f"{label}: clause_node_count {checks['clause_node_count']} != {expected['clause_node_count']}")
    if console_errors:
        violations.append(f"console errors: {console_errors}")

    status = "PASS" if not violations else "FAIL"
    result = {
        "status": status,
        "case_id": case_id,
        "html_path": str(html_path),
        "screenshots": screenshots,
        "layout_checks": layout_checks,
        "console_messages": console_messages,
        "console_errors": console_errors,
        "network_responses": responses,
        "violations": violations,
    }
    _write_json(out_dir / "browser_result.json", result)
    _write_json(out_dir / "browser_console.json", console_messages)
    _write_json(out_dir / "browser_network.json", responses)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
