"""thoughts — 从结构化 Agent 结果自动生成 reasoning summary。"""

from __future__ import annotations

from typing import Any


def summarize_agent_output(
    agent_name: str,
    result: Any,
    *,
    input_hint: str = "",
) -> str:
    """基于 Agent 结构化输出生成一句中文思路摘要。

    规则驱动，优先从结构化字段提取关键信息，不暴露原始 CoT。
    """

    # ── 尝试结构化字段提取 ──
    if hasattr(result, "model_dump"):
        data: dict[str, Any] = result.model_dump()
    elif isinstance(result, dict):
        data = result
    else:
        return f"{agent_name} 执行完成"

    # ── gap_candidates / contract_gaps ──
    gaps = data.get("gap_candidates") or data.get("contract_gaps") or []
    if isinstance(gaps, list) and gaps:
        high = sum(1 for g in (gaps if isinstance(gaps, list) else []) if _level_of(g) == "HIGH")
        medium = sum(1 for g in (gaps if isinstance(gaps, list) else []) if _level_of(g) == "MEDIUM")
        parts = [f"{len(gaps)} 个差距项"]
        if high:
            parts.append(f"{high} 项高风险")
        if medium:
            parts.append(f"{medium} 项中风险")
        return f"{agent_name}：{'，'.join(parts)}"

    # ── issues ──
    issues = data.get("issues") or data.get("consistency_issues") or []
    if isinstance(issues, list) and issues:
        return f"{agent_name}：发现 {len(issues)} 个问题"

    # ── fact_packs / facts ──
    facts = data.get("facts") or data.get("fact_packs") or []
    if isinstance(facts, list) and facts:
        return f"{agent_name}：提取 {len(facts)} 条结构化事实"

    # ── chapters ──
    chapters = data.get("chapters") or []
    if isinstance(chapters, list) and chapters:
        return f"{agent_name}：生成 {len(chapters)} 个章节"

    # ── diagnosis result ──
    path = data.get("recommended_path") or data.get("path")
    if isinstance(path, str) and path.strip():
        risk = data.get("risk_level", "")
        return f"{agent_name}：推荐路径 {path}" + (f"（风险 {risk}）" if risk else "")

    # ── overall rating ──
    rating = data.get("overall_rating") or data.get("risk_level") or data.get("overall_traffic_light")
    if isinstance(rating, str) and rating.strip():
        return f"{agent_name}：综合评级 {rating}"

    # ── retrieval hit ──
    hits = data.get("hits") or data.get("regulations") or []
    if isinstance(hits, list) and hits:
        return f"{agent_name}：检索命中 {len(hits)} 条"

    # ── counts ──
    count_keys = ["findings", "assessment_items", "review_items", "evidence_items"]
    for key in count_keys:
        items = data.get(key, [])
        if isinstance(items, list) and items:
            return f"{agent_name}：输出 {len(items)} 项"

    return f"{agent_name} 执行完成"


def _level_of(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("risk_level", "")).upper()
    if hasattr(item, "risk_level"):
        return str(getattr(item, "risk_level")).upper()
    return ""
