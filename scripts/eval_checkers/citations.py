"""Citation dimension checker — evaluates whether citations are clickable, hoverable, and jumpable."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


def check_citations(
    task_id: str,
    module: str,
    base_url: str = "http://127.0.0.1:8000",
    auth_token: str = "",
) -> dict[str, Any]:
    """Run citation audit for one task run.

    Returns a dict with score (0-100) and detailed findings for each citation.
    """
    findings: dict[str, Any] = {
        "task_id": task_id,
        "module": module,
        "citation_map_exists": False,
        "citation_count": 0,
        "citations": [],
        "score": 0,
        "issues": [],
        "summary": "",
    }

    # ── 1. Fetch citation_map via API ──
    url = f"{base_url}/api/v1/citations/reports/{task_id}?module={module}"
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        findings["issues"].append(f"Citation API returned HTTP {e.code}")
        findings["summary"] = f"Citation API unreachable (HTTP {e.code}) — citations not clickable"
        return findings
    except Exception as e:
        findings["issues"].append(f"Citation API error: {e}")
        findings["summary"] = f"Citation API error — citations not clickable"
        return findings

    footnote_map = data.get("footnote_map", {})
    all_items = data.get("all_items", []) or list(footnote_map.values())

    findings["citation_map_exists"] = len(footnote_map) > 0 or len(all_items) > 0
    findings["citation_count"] = len(all_items) if all_items else len(footnote_map)

    if not findings["citation_map_exists"]:
        findings["issues"].append("citation_map.json is empty or does not exist — no clickable citations")
        findings["summary"] = "Module has NO clickable citations"
        return findings

    # ── 2. Analyze each citation ──
    score_total = 0
    max_per_item = 25  # max points per citation

    items_to_check = all_items if all_items else [footnote_map[k] for k in footnote_map]

    for i, item in enumerate(items_to_check):
        cit: dict[str, Any] = {
            "index": i + 1,
            "title": item.get("title", ""),
            "article_no": item.get("article_no", ""),
            "has_knowledge_url": False,
            "knowledge_url": "",
            "knowledge_url_reachable": False,
            "has_quote_text": False,
            "has_authority_level": False,
            "has_confidence_score": False,
            "score": 0,
        }

        # Sub-checks
        knowledge_url = item.get("knowledge_url", "")
        cit["knowledge_url"] = knowledge_url
        cit["has_knowledge_url"] = bool(knowledge_url)
        if cit["has_knowledge_url"]:
            cit["score"] += 5

        if knowledge_url.startswith("http"):
            full_url = knowledge_url
        elif knowledge_url.startswith("/"):
            full_url = f"{base_url}{knowledge_url}"
        else:
            full_url = ""

        if full_url:
            try:
                req2 = urllib.request.Request(full_url)
                with urllib.request.urlopen(req2, timeout=5) as resp2:
                    if resp2.status == 200:
                        cit["knowledge_url_reachable"] = True
                        cit["score"] += 5
            except Exception:
                pass

        if item.get("quote_text"):
            cit["has_quote_text"] = True
            cit["score"] += 5

        if item.get("authority_level"):
            cit["has_authority_level"] = True
            cit["score"] += 5

        if "confidence_score" in item or item.get("confidence_score", 0) > 0:
            cit["has_confidence_score"] = True
            cit["score"] += 5

        findings["citations"].append(cit)
        score_total += cit["score"]

    # ── 3. Compute final score ──
    max_possible = len(items_to_check) * max_per_item
    findings["score"] = round((score_total / max_possible * 100), 1) if max_possible > 0 else 0

    if findings["score"] >= 80:
        findings["summary"] = f"Citations fully functional: {findings['score']}%"
    elif findings["score"] >= 40:
        findings["summary"] = f"Citations partially functional: {findings['score']}% — gaps found"
    elif findings["citation_map_exists"]:
        findings["summary"] = f"Citations exist but poorly formed: {findings['score']}%"
    else:
        findings["summary"] = "No citations available"

    return findings
