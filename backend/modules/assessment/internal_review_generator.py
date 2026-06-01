from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from backend.common.workflow import IssueItem

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient


_SYSTEM_PROMPT = (
    "你是企业内部合规风险解释 Agent。你的输出给企业法务、合规负责人和项目人员自己看，"
    "不是对外正式文书。请直接指出风险、缺失证据、不能直接写入正式文书的表述和下一步补充材料。"
)


def build_internal_review_payload(
    *,
    issues: list[IssueItem],
    writing_strategy: dict[str, Any],
    generation_basis_pack: dict[str, Any],
    material_rows: list[dict[str, str]],
) -> dict[str, Any]:
    high_risk = [issue for issue in issues if issue.severity in {"HIGH", "BLOCKER"}]
    strategy_items = writing_strategy.get("strategies", [])
    forbidden = sorted(
        {
            item
            for strategy in strategy_items
            if isinstance(strategy, dict)
            for item in strategy.get("forbidden_expressions", [])
            if isinstance(item, str)
        }
    )
    return {
        "module": "assessment",
        "overall_risk": "HIGH" if high_risk else ("MEDIUM" if issues else "LOW"),
        "high_risk_issues": [issue.model_dump() for issue in high_risk],
        "all_issues": [issue.model_dump() for issue in issues],
        "material_checklist": material_rows,
        "forbidden_external_expressions": forbidden,
        "writing_strategies": strategy_items,
        "basis_pack_ref": {
            "task_id": generation_basis_pack.get("task_id"),
            "issue_count": len(generation_basis_pack.get("issues", [])),
            "evidence_count": len(generation_basis_pack.get("evidence_chain", [])),
            "regulation_count": len(generation_basis_pack.get("regulations", [])),
        },
        "legal_grounding": generation_basis_pack.get("legal_grounding", {"by_issue": {}}),
    }


def generate_internal_review_markdown(
    *,
    payload: dict[str, Any],
    llm_client: "LLMClient | None" = None,
) -> str:
    if llm_client and llm_client.enabled:
        user_prompt = (
            "请基于以下结构化风险数据生成内部 AI 检验文本。\n"
            "必须包含：总体风险判断、高风险问题、证据不足项、不能写入正式文书的表述、"
            "用户下一步应补充的材料。\n"
            "要求：直接、清楚、中文输出，不要写成正式报告语言。\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        text = llm_client.chat(system=_SYSTEM_PROMPT, user=user_prompt, temperature=0.2, max_tokens=1600)
        if text and "LLM服务暂时不可用" not in text:
            return text.strip()

    lines = [
        "# 内部 AI 检验文本",
        "",
        f"## 总体风险判断",
        "",
        f"当前综合风险等级：{payload.get('overall_risk', 'MEDIUM')}。该结论仅供内部审查和补充材料使用，不作为对外正式结论。",
        "",
        "## 高风险问题",
        "",
    ]
    high_risk = payload.get("high_risk_issues", [])
    if high_risk:
        for issue in high_risk:
            lines.append(f"- **{issue.get('title', '未命名问题')}**：{issue.get('description', '')}")
            lines.append(f"  建议：{issue.get('recommended_action', '')}")
    else:
        lines.append("- 暂未识别到 HIGH/BLOCKER 级别问题，但仍需人工复核。")

    lines.extend(["", "## 证据不足与材料补充", ""])
    materials = payload.get("material_checklist", [])
    if materials:
        for item in materials:
            lines.append(f"- {item.get('source_ref', '材料')}：{item.get('summary', '')}（{item.get('status', '待补充')}）")
    else:
        lines.append("- 当前未形成明确材料补充清单。")

    lines.extend(["", "## 正式文书中不宜直接出现的表述", ""])
    forbidden = payload.get("forbidden_external_expressions", [])
    if forbidden:
        for item in forbidden:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂未生成禁止性表述清单。")

    lines.extend(["", "## 内外表达策略", ""])
    for strategy in payload.get("writing_strategies", []):
        lines.append(f"- **{strategy.get('issue_id', '')}**")
        lines.append(f"  - 内部说明：{strategy.get('internal_expression', '')}")
        lines.append(f"  - 对外表达：{strategy.get('external_expression', '')}")

    return "\n".join(lines).strip() + "\n"
