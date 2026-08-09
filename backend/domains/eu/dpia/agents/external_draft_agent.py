"""Agent 7: ExternalDPIAgent — generate DPIA chapters with strict template and citation constraints.

Solves: plain ChapterGenerator can write text, but DPIA needs strong template control.
Must follow ICO DPIA template, only use registered citations, and use conservative language
for user_claim_only facts.

Reference: docs/archive/design-provenance/dpia.md Section 8
"""

from __future__ import annotations

from backend.common.llm.postprocess import apply_citation_pipeline
from backend.domains.eu.dpia.agents import DPIAAgentBase
from backend.domains.eu.dpia.deterministic_chapters import build_deterministic_chapter


# ── Key constraints for DPIA draft generation ──

DPIA_DRAFT_CONSTRAINTS = """写作约束：
1. 你生成的是 DPIA 草案，不是法律意见书。
2. 必须严格按照模板章节输出，不得合并或跳过章节。
3. 不得编造事实 — 仅使用上下文提供的事实。
4. 不得编造法规引用 — 仅使用上下文提供的citation。
5. 不得将 planned measure 写成 implemented measure。
6. 不得写"风险已完全消除" — 始终说明剩余风险。
7. 高风险必须说明可能性、影响和缓解措施。
8. 对user_claim_only的事实使用保守表达（如"用户表示..."而非"已确认..."）。
9. 缺少证据时写"需补充证据"，不得跳过。
10. 每个法律结论必须有法规引用。
11. 法规引用只能使用“法规依据”中提供的完整 {{CIT-...}} 标记，禁止使用来源 ID、CIT-001 或文字引用代替。"""

DPIA_CHAPTER_TITLES_CN = {
    "need_identification": "1. 识别 DPIA 需求",
    "processing_description": "2. 描述处理活动",
    "consultation": "3. 咨询过程",
    "necessity_proportionality": "4. 必要性与相称性评估",
    "risk_assessment": "5. 识别与评估风险",
    "mitigation": "6. 降低风险的措施",
    "signoff": "7. 签署与记录",
}


class ExternalDPIAgent(DPIAAgentBase):
    agent_name = "dpia_external_draft"
    max_tokens = 2500

    def run(
        self,
        section_pack: dict | None = None,
        generation_basis_pack: dict | None = None,
        writing_strategy: dict | None = None,
        citation_registry=None,
    ) -> list[dict]:
        """Generate DPIA draft chapters from generation basis pack.

        Each chapter receives structured context including facts, issues, risk matrix,
        mitigation plan, legal grounding, and citations.
        """
        section_pack = section_pack or {}
        gen_basis = generation_basis_pack or {}
        writing = writing_strategy or {}

        if not self.enabled:
            return _placeholder_chapters(gen_basis)

        # Generate chapters individually
        chapters: list[dict] = []
        chapter_ids = list(DPIA_CHAPTER_TITLES_CN.keys())
        section_packs = {
            item.get("section_id"): item
            for item in gen_basis.get("section_packs", [])
            if isinstance(item, dict) and item.get("section_id")
        }

        for i, chapter_id in enumerate(chapter_ids, 1):
            title = DPIA_CHAPTER_TITLES_CN.get(chapter_id, chapter_id)
            section = section_packs.get(
                chapter_id,
                gen_basis.get(chapter_id, gen_basis.get("sections", {}).get(chapter_id, {})),
            )

            chapter_prompt = _build_chapter_prompt(
                chapter_id=chapter_id,
                title=title,
                section=section,
                gen_basis=gen_basis,
                writing=writing,
            )

            result = self._call_llm(chapter_prompt)
            if result is None:
                fallback = build_deterministic_chapter(
                    chapter_id=chapter_id,
                    title=title,
                    section=section,
                    generation_basis_pack=gen_basis,
                    citation_registry=citation_registry,
                )
                chapters.append({"chapter_no": i, **fallback})
            else:
                content = apply_citation_pipeline(
                    result.get("content", result.get("draft_text", "")),
                    registry=citation_registry,
                    allowed_citations=[
                        item.display_label for item in citation_registry
                    ] if citation_registry is not None else [],
                ).text
                chapters.append({
                    "chapter_no": i,
                    "title": title,
                    "content": content,
                    "citations": result.get("citations", []),
                    "risk_level": result.get("risk_level", "medium"),
                })

        return chapters


def _build_chapter_prompt(
    chapter_id: str,
    title: str,
    section: dict,
    gen_basis: dict,
    writing: dict,
) -> str:
    """Build chapter-specific prompt with writing strategy constraints."""
    # ``build_generation_basis_pack`` is the canonical producer and names
    # the complete request-derived fact list ``user_facts``.  Keep the older
    # aliases as read-only fallbacks for stored/replayed packs.
    has_section_contract = bool(section)
    facts_source = (
        section.get("confirmed_facts", [])
        if has_section_contract
        else gen_basis.get("user_facts", gen_basis.get("facts", gen_basis.get("all_facts", [])))
    )
    issues_source = (
        section.get("issues", [])
        if has_section_contract
        else gen_basis.get("issues", gen_basis.get("all_issues", []))
    )
    facts_brief = _format_facts(facts_source)
    issues_brief = _format_issues(issues_source)
    risk_brief = _format_risks(
        gen_basis.get("risk_matrix", [])
        if chapter_id in {"risk_assessment", "mitigation", "signoff"}
        else []
    )
    mit_brief = _format_mitigation(
        gen_basis.get("mitigation_plan", [])
        if chapter_id in {"mitigation", "signoff"}
        else []
    )
    dpo_brief = _format_dpo(
        gen_basis.get("dpo_decision_pack", {})
        if chapter_id in {"need_identification", "consultation", "signoff"}
        else {}
    )
    citations_brief = _format_citations(
        gen_basis.get("citations", gen_basis.get("regulations", []))
    )
    legal_brief = _format_legal(
        section.get("legal_grounding", [])
        if has_section_contract
        else gen_basis.get("legal_grounding", {})
    )
    need_brief = _format_need(gen_basis.get("need_assessment", {}))

    chapter_strategy = writing.get("chapters", {}).get(chapter_id, {})
    forbidden = chapter_strategy.get("forbidden_expressions", writing.get("forbidden_expressions", []))

    return f"""{DPIA_DRAFT_CONSTRAINTS}

生成 DPIA 章节：{title}

项目事实：
{facts_brief}

DPIA 需求判断：
{need_brief}

已识别问题：
{issues_brief}

风险矩阵：
{risk_brief}

缓解措施：
{mit_brief}

DPO 意见：
{dpo_brief}

法规依据：
{citations_brief}

法律基础：
{legal_brief}

禁止表达：{', '.join(forbidden) if forbidden else '无特殊限制'}

输出JSON：
{{
  "content": "<chapter content in professional Chinese, 3-5 paragraphs>",
  "citations": ["CIT-xxx"],
  "risk_level": "low" | "medium" | "high"
}}

{chapter_id}章节要点：
- need_identification: 说明WP248 criteria命中情况，DPIA触发的法律依据
- processing_description: 系统性描述数据流、数据类型、数量、保留期、跨境情况
- consultation: 记录内部/外部/DPO咨询过程和意见
- necessity_proportionality: 评估每项处理的必要性和相称性，指出过度处理
- risk_assessment: 每个风险的可能性、影响、受影响权利
- mitigation: 每个措施的现状（planned/implemented）和有效性
- signoff: DPO结论、条件、监管咨询建议"""


def _placeholder_chapters(gen_basis: dict) -> list[dict]:
    """Backward-compatible no-provider path using structured chapter fallbacks."""
    section_packs = {
        item.get("section_id"): item
        for item in gen_basis.get("section_packs", [])
        if isinstance(item, dict) and item.get("section_id")
    }
    chapters: list[dict] = []
    for i, (cid, title) in enumerate(DPIA_CHAPTER_TITLES_CN.items(), 1):
        fallback = build_deterministic_chapter(
            chapter_id=cid,
            title=title,
            section=section_packs.get(cid, {}),
            generation_basis_pack=gen_basis,
        )
        chapters.append({"chapter_no": i, **fallback})
    return chapters


# ── Formatting helpers ──

def _format_facts(facts: list) -> str:
    if not facts:
        return "未提供"
    lines = []
    for f in facts[:15]:
        if hasattr(f, "value"):
            lines.append(f"- [{getattr(f, 'evidence_status', '?')}] {getattr(f, 'value', str(f))}")
        elif isinstance(f, dict):
            lines.append(f"- [{f.get('evidence_status', '?')}] {f.get('value', str(f))}")
    return "\n".join(lines)

def _format_issues(issues: list) -> str:
    if not issues:
        return "无"
    lines = []
    for i in issues[:10]:
        if hasattr(i, "title"):
            lines.append(f"- [{getattr(i, 'severity', '?')}] {getattr(i, 'title', str(i))}")
        elif isinstance(i, dict):
            lines.append(f"- [{i.get('severity', '?')}] {i.get('title', str(i))}")
    return "\n".join(lines)

def _format_risks(risks: list) -> str:
    if not risks:
        return "无风险矩阵"
    lines = []
    for r in risks[:8]:
        if isinstance(r, dict):
            lines.append(f"- [{r.get('overall_level', '?')}] {r.get('risk_name', r.get('risk_id', ''))}: {r.get('description', '')[:80]}")
    return "\n".join(lines)

def _format_mitigation(plan: list) -> str:
    if not plan:
        return "无缓解计划"
    lines = []
    for entry in plan[:5]:
        if isinstance(entry, dict):
            measures = entry.get("measures", [])
            for m in measures[:2]:
                lines.append(f"- [{m.get('status', '?')}] {m.get('measure', '')[:80]}")
    return "\n".join(lines) or "无措施"

def _format_dpo(dpo: dict) -> str:
    if not dpo:
        return "未提供DPO意见"
    return f"Position: {dpo.get('dpo_position', '?')}. Conditions: {dpo.get('conditions', [])}. Prior consultation: {dpo.get('prior_consultation_recommended', '?')}"

def _format_citations(citations: list) -> str:
    if not citations:
        return "无引用"
    lines: list[str] = []
    for citation in citations:
        if isinstance(citation, dict):
            rule_id = citation.get(
                "citation_id",
                citation.get("rule_id", citation.get("source_id", "")),
            )
            title = citation.get("title", "")
            article = citation.get("article", citation.get("article_no", ""))
            lines.append(f"{{{{{rule_id}}}}} {title} {article}".strip())
        else:
            lines.append(str(citation)[:120])
    return "\n".join(lines) or "无引用"

def _format_legal(legal: object) -> str:
    if not legal:
        return "未提供"
    if isinstance(legal, list):
        lines = [
            f"- {item.get('issue_id', '')}: {item.get('title', '')} "
            f"{item.get('article', '')} (confidence={item.get('confidence_score', 'N/A')})"
            for item in legal[:8]
            if isinstance(item, dict)
        ]
        return "\n".join(lines) or "未提供"
    if isinstance(legal, dict):
        by_issue = legal.get("by_issue")
        if isinstance(by_issue, dict):
            flattened = [
                item
                for items in by_issue.values()
                if isinstance(items, list)
                for item in items
                if isinstance(item, dict)
            ]
            return _format_legal(flattened)
        issues = legal.get("issue_legal_mapping", legal.get("legal_basis", {}))
        return str(issues)[:600]
    return str(legal)[:600]

def _format_need(need: dict) -> str:
    if not need:
        return "未提供"
    return f"Required: {need.get('dpia_required', '?')}. Triggers: {need.get('trigger_reasons', [])}"
