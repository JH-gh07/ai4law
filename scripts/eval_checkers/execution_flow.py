"""Execution flow dimension checker — evaluates trace events and token statistics."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

ALL_EVENT_TYPES = {
    "status", "thought", "tool_start", "tool_result",
    "intermediate", "warning", "final", "final_brief",
}


def check_execution_flow(
    task_id: str,
    module: str,
    base_url: str = "http://127.0.0.1:8000",
    auth_token: str = "",
) -> dict[str, Any]:
    """Run execution flow audit for one task run.

    Returns a dict with score (0-100), event type coverage, and token statistics.
    """
    findings: dict[str, Any] = {
        "task_id": task_id,
        "module": module,
        "total_events": 0,
        "event_types_found": [],
        "event_types_missing": list(ALL_EVENT_TYPES),
        "type_coverage_pct": 0,
        "has_token_data": False,
        "token_by_stage": [],
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "score": 0,
        "issues": [],
        "summary": "",
    }

    # ── 1. Fetch trace events ──
    url = f"{base_url}/api/v1/events/task/{task_id}/events?since=0"
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        findings["issues"].append(f"Events API returned HTTP {e.code}")
        findings["summary"] = f"Trace API unreachable (HTTP {e.code}) — execution flow not visible"
        return findings
    except Exception as e:
        findings["issues"].append(f"Events API error: {e}")
        findings["summary"] = f"Trace API error — execution flow not visible"
        return findings

    events = data.get("events", [])
    findings["total_events"] = len(events)

    if len(events) == 0:
        findings["issues"].append("No trace events found — execution timeline will be empty")
        findings["summary"] = "No execution trace available"
        return findings

    # ── 2. Event type coverage ──
    found_types = set()
    token_stages: list[dict] = []
    total_input = 0
    total_output = 0

    for event in events:
        etype = event.get("event_type", "")
        found_types.add(etype)
        detail = event.get("detail") or {}

        # Check for token data in any field
        tc = detail.get("token_count") or detail.get("tokens") or detail.get("token_usage")
        if tc:
            if isinstance(tc, dict):
                inp = tc.get("input") or tc.get("prompt_tokens") or 0
                out = tc.get("output") or tc.get("completion_tokens") or 0
            else:
                inp, out = 0, 0

            total_input += int(inp) if inp else 0
            total_output += int(out) if out else 0
            token_stages.append({
                "event_type": etype,
                "seq": event.get("seq"),
                "summary": event.get("summary", "")[:80],
                "token_input": int(inp) if inp else 0,
                "token_output": int(out) if out else 0,
            })

    findings["event_types_found"] = sorted(found_types)
    findings["event_types_missing"] = sorted(ALL_EVENT_TYPES - found_types)
    findings["type_coverage_pct"] = round(len(found_types) / len(ALL_EVENT_TYPES) * 100, 1)
    findings["has_token_data"] = len(token_stages) > 0
    findings["token_by_stage"] = token_stages
    findings["total_tokens_input"] = total_input
    findings["total_tokens_output"] = total_output

    # ── 3. Score ──
    # Event type coverage: 50% of total
    # Token data availability: 50% of total
    coverage_score = findings["type_coverage_pct"] * 0.5
    token_score = (50 if findings["has_token_data"] else 0)
    findings["score"] = round(coverage_score + token_score, 1)

    if findings["score"] >= 80:
        findings["summary"] = f"Execution flow fully functional: {findings['score']}%"
    elif len(events) > 0:
        findings["summary"] = f"Execution flow partially functional: {findings['score']}% — {findings['total_events']} events, {len(found_types)}/{len(ALL_EVENT_TYPES)} event types covered"
    else:
        findings["summary"] = "No execution trace available"

    if not findings["has_token_data"]:
        findings["issues"].append("No token_count data found in any trace event detail")

    return findings
