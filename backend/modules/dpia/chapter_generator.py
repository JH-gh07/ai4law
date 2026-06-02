"""DPIA chapter generator — produces 7 DPIA template sections aligned with GDPR Art 35 and ICO guidance."""

from __future__ import annotations

from backend.common.llm.client import LLMClient
from backend.common.llm.postprocess import convert_citation_markers, ensure_paragraph_citations
from backend.common.workflow import GenerationContextPack
from backend.modules.dpia.generation_basis import DPIA_CHAPTER_ID_TO_TITLE
from backend.modules.dpia.schema import DPIAChapterContent

DPIA_CHAPTER_KEYS = [k for k in DPIA_CHAPTER_ID_TO_TITLE]

_SYSTEM_PROMPT = (
    "你是一名专注于欧盟 GDPR 合规的资深数据保护律师，深度掌握 GDPR、WP29 指南、"
    "EDPB 指南、WP248（DPIA 高风险标准）、WP251（自动化决策）、ICO DPIA 实践指南等法规与指引。"
    "请严格按照 ICO DPIA 模板的行文规范，用专业、严谨的中文撰写 DPIA 草案各章节内容。"
    "每章节结构清晰、有据可查，避免空话套话，直接针对项目实际情况进行分析。"
    "引用法规时应写明具体条文（如 GDPR Art 35(7)(b)），区分法规要求与项目实践。"
)

_STRICT_CONSTRAINT = (
    "写作约束：仅使用上下文提供的事实、issue 与法规条文，不得新增数据类别、数据主体、"
    "处理目的、技术方案或业务场景。若上下文缺失，请写「未提供」或「需补充」。"
    "如需推测，请明确标注【推测】。每个风险判断必须引用上下文中的 issue_id 或法规 citation。"
    "对材料缺失只能写「需补充/待补充」，不得假设材料已经具备。"
    "\n\n引用约束（必须遵守）："
    "\n- 下方【可引用法规依据】提供了可用依据，每条格式为 {{CIT-xxx}} = 法规名 条文"
    "\n- 需要引用法规时，在句末使用 {{CIT-xxx}} 标记"
    "\n- 禁止使用其他引用格式，禁止编造不在列表中的法规依据"
    "\n- 一个观点可引用多条：{{CIT-xxx}}{{CIT-yyy}}"
    "\n- 若无可引用，写「【依据：未检索到相关法规】」"
    "\n\n表达策略硬约束（必须遵守）："
    "\n1. 对外报告只能使用各 issue 的 external_expression 表述，不得使用 internal_expression。"
    "\n2. 不得在报告中出现【全局禁用表达】中列出的任何措辞或近义表述。"
    "\n3. 对于材料缺失/证据不足的 issue，采用审慎保守表述，不得作出正面承诺或确定性结论。"
    "\n4. user_claim_only 类型的事实（标注 evidence_status=user_claim_only）不得作为外部正面结论的唯一依据。"
    "\n5. 在 signoff 章节，如 prior_consultation_possible 为 True，必须明确声明残余高风险并建议依据 GDPR Art 36 事先咨询。"
)

_CHAPTER_PROMPTS: dict[str, str] = {
    "need_identification": (
        "请根据以下项目信息，撰写 DPIA 草案第一章「识别需求 (Identify Need for DPIA)」，"
        "包含：(1) 项目的基本背景和目的；(2) DPIA 触发理由——具体说明哪些 WP248 高风险标准被触发；"
        "(3) 适用的法律依据（GDPR Art 35 及具体的 WP248 标准）；"
        "(4) 是否可能需要进行监管机构事先咨询（GDPR Art 36）。"
        "请使用项目事实而非泛泛而谈。"
    ),
    "processing_description": (
        "请根据以下项目信息，撰写 DPIA 草案第二章「描述处理活动 (Describe the Processing)」，"
        "包含：(1) 数据收集、使用、存储、删除的全生命周期描述；"
        "(2) 数据类别清单（含特殊类别数据的标注）；"
        "(3) 数据主体类别及大致数量；"
        "(4) 是否涉及自动化决策/画像、系统性监控、跨境传输、数据匹配、新技术使用；"
        "(5) 数据保留期限。"
        "对任何缺失信息标注「需补充」。"
    ),
    "consultation": (
        "请根据以下项目信息，撰写 DPIA 草案第三章「咨询过程 (Consultation Process)」，"
        "包含：(1) 内部咨询情况——咨询了哪些部门/职能（法务、安全、业务等）；"
        "(2) 外部专家咨询情况；"
        "(3) 数据主体咨询计划（是否计划以及如何征询数据主体或其代表意见）；"
        "(4) DPO 是否已参与审查。"
        "如某方面为空，标注「尚未咨询/未提供」并建议补充。"
    ),
    "necessity_proportionality": (
        "请根据以下项目信息，撰写 DPIA 草案第四章「必要性与相称性 (Necessity & Proportionality)」，"
        "包含：(1) 合法性基础分析——逐一说明所依赖的 GDPR Art 6 合法性基础及其适用论证；"
        "(2) 如有特殊类别数据，说明适用的 GDPR Art 9 豁免条件；"
        "(3) 必要性论证——为何必须处理该等个人数据，为何无法以侵入性更低的方式实现目的；"
        "(4) 相称性分析——处理范围、频率和存储期限与处理目的是否相称；"
        "(5) 透明度评估——数据主体告知（GDPR Art 13/14）的安排是否充分。"
        "对必要性/相称性简短或缺失的，明确标注论证不充分的缺陷。"
    ),
    "risk_assessment": (
        "请根据以下项目信息，撰写 DPIA 草案第五章「风险识别与评估 (Identify & Assess Risks)」，"
        "包含：(1) 逐项列出已识别的风险，以风险矩阵形式呈现（风险描述 | 可能性 | 影响程度 | 风险等级）；"
        "(2) 每项风险的来源分析（处理活动/数据类型/技术/第三方/组织因素）；"
        "(3) 受影响的数据主体群体；"
        "(4) 重点关注：自动化决策叠加特殊类别数据的歧视风险、跨境传输的接收方保护水平不足风险、"
        "弱势数据主体的权利不对等风险。"
        "确保每个风险有事实依据支撑，不得凭空列举。"
    ),
    "mitigation": (
        "请根据以下项目信息，撰写 DPIA 草案第六章「降低风险的措施 (Mitigation Measures)」，"
        "包含：(1) 逐项列出已计划的缓解措施，需对应到第五章的具体风险；"
        "(2) 每项措施的实施状态（planned/in_progress/implemented/verified）；"
        "(3) 负责方；"
        "(4) 实施后的残余风险水平评估；"
        "(5) 对未覆盖风险的识别——如某项 HIGH 风险无对应缓解措施，需明确标注。"
        "缓解措施应具体可验证，避免模糊承诺。"
    ),
    "signoff": (
        "请根据以下项目信息，撰写 DPIA 草案第七章「签署与记录 (Sign Off & Record Outcomes)」，"
        "包含：(1) DPIA 负责人信息；"
        "(2) DPO 审查意见（如已出具）；"
        "(3) 整体 DPIA 结论——是否接受残余风险水平；"
        "(4) 是否需要依据 GDPR Art 36 进行监管机构事先咨询；"
        "(5) 复审日期和触发复审的条件（重大变更时重新评估的要求）。"
        "如 prior_consultation_possible 为 True，必须明确建议准备事先咨询材料。"
        "如 DPO 意见缺失，必须标注为待补充事项。"
    ),
}

# Reverse mapping: chapter_id → title
_CHAPTER_TITLES = {v: k for k, v in DPIA_CHAPTER_ID_TO_TITLE.items() if False}  # unused; kept for completeness


def _format_fact_value(value: object) -> str:
    if isinstance(value, list):
        return "、".join(str(item) for item in value) if value else "未提供"
    if value is True:
        return "是"
    if value is False:
        return "否"
    if value is None or value == "":
        return "未提供"
    return str(value)


def build_context_block_from_pack(context_pack: GenerationContextPack, chapter_id: str) -> str:
    """Build a rich context block for a single DPIA chapter from the generation basis pack."""
    section_pack = None
    if context_pack.generation_basis_pack:
        section_packs = context_pack.generation_basis_pack.get("section_packs", [])
        for sp in section_packs:
            if sp.get("section_id") == chapter_id:
                section_pack = sp
                break

    diagnosis = context_pack.diagnosis_result or {}

    if section_pack:
        fact_lines = [
            f"- {fact.get('field_path', fact.get('fact_id', ''))}：{_format_fact_value(fact.get('value'))}"
            for fact in section_pack.get("confirmed_facts", [])
        ] or ["- 本章节无确认事实"]
        regulation_lines = [
            "- {rule_id} | {title} {article}：{snippet}".format(
                rule_id=item.get("rule_id", "unknown"),
                title=item.get("title", ""),
                article=item.get("article", ""),
                snippet=str(item.get("snippet", ""))[:160],
            )
            for item in section_pack.get("legal_basis", [])[:5]
        ] or ["- 未检索到法规依据"]

        matched_issues = [
            issue for issue in context_pack.issues if chapter_id in issue.affects_outputs
        ]
        if not matched_issues:
            matched_issues = [
                issue for issue in context_pack.issues if issue.severity in {"HIGH", "BLOCKER"}
            ]
        issue_lines = [
            f"- {issue.issue_id} | {issue.severity} | {issue.title}："
            f"{issue.description}；建议：{issue.recommended_action}"
            for issue in matched_issues
        ] or ["- 未识别到与本章节直接相关的问题项"]

        chapter_issue_ids = {issue.issue_id for issue in matched_issues}
        ws_items = section_pack.get("writing_strategies", [])
        strategy_lines = [
            f"- {s.get('issue_id', '')} | external_expression: {s.get('external_expression', '')}"
            f" | forbidden: {', '.join(s.get('forbidden_expressions', [])[:3])}"
            for s in ws_items if s.get("issue_id") in chapter_issue_ids
        ] or ["- 本章节无特定表达策略约束"]
        global_forbidden: list[str] = (
            context_pack.writing_strategy.get("global_forbidden_expressions", [])
            if context_pack.writing_strategy else []
        )

        grounding_lines: list[str] = []
        lg_items = section_pack.get("legal_grounding", [])
        for binding in lg_items[:4]:
            grounding_lines.append(
                f"- {binding.get('issue_id', '')} → {binding.get('title', '')} "
                f"{binding.get('article', '')}"
                f" (confidence: {binding.get('confidence_score', 'N/A')})"
            )
        if not grounding_lines:
            grounding_lines = ["- 本章节无精确法规绑定"]
    else:
        fact_lines = [
            f"- {fact.field_path or fact.fact_id}：{_format_fact_value(fact.normalized_value)}"
            for fact in context_pack.facts
            if fact.source_type in {"schema", "diagnosis"}
        ]
        regulation_lines = [
            "- {source_id} | {title} {article}：{snippet}".format(
                source_id=item.get("source_id", "unknown"),
                title=item.get("title", ""),
                article=item.get("article", ""),
                snippet=str(item.get("snippet", ""))[:160],
            )
            for item in context_pack.regulations[:5]
        ] or ["- 未检索到法规依据"]

        matched_issues = [
            issue for issue in context_pack.issues if chapter_id in issue.affects_outputs
        ]
        if not matched_issues:
            matched_issues = [
                issue for issue in context_pack.issues if issue.severity in {"HIGH", "BLOCKER"}
            ]
        issue_lines = [
            f"- {issue.issue_id} | {issue.severity} | {issue.title}："
            f"{issue.description}；建议：{issue.recommended_action}"
            for issue in matched_issues
        ] or ["- 未识别到与本章节直接相关的问题项"]

        strategy_lines: list[str] = []
        global_forbidden: list[str] = []
        if context_pack.writing_strategy:
            global_forbidden = context_pack.writing_strategy.get("global_forbidden_expressions", [])
            strategies = context_pack.writing_strategy.get("strategies", [])
            chapter_issue_ids = {issue.issue_id for issue in matched_issues}
            chapter_strategies = [
                s for s in strategies if s.get("issue_id") in chapter_issue_ids
            ]
            strategy_lines = [
                f"- {s['issue_id']} | external_expression: {s.get('external_expression', '')}"
                f" | forbidden: {', '.join(s.get('forbidden_expressions', [])[:3])}"
                for s in chapter_strategies
            ] or ["- 本章节无特定表达策略约束"]
        else:
            strategy_lines = ["- 未启用表达策略约束"]

        grounding_lines: list[str] = []
        if context_pack.legal_grounding:
            by_issue = context_pack.legal_grounding.get("by_issue", {})
            chapter_issue_ids = {issue.issue_id for issue in matched_issues}
            for issue_id in chapter_issue_ids:
                bindings = by_issue.get(issue_id, [])
                for binding in bindings[:2]:
                    grounding_lines.append(
                        f"- {issue_id} → {binding.get('title', '')} {binding.get('article', '')}"
                        f" (confidence: {binding.get('confidence_score', 'N/A')})"
                    )
        if not grounding_lines:
            grounding_lines = ["- 本章节无精确法规绑定"]

    attachment_lines: list[str] = []
    for item in context_pack.attachment_notes:
        source_ref = item.get("source_ref", "attachment")
        atype = item.get("type", "")
        type_tag = f"[{atype}] " if atype and atype != "other" else ""
        summary = item.get("summary", "")
        line = f"- {source_ref}：{type_tag}{summary}"
        if item.get("missing_core_clauses"):
            line += f" (缺失条款: {item['missing_core_clauses']})"
        attachment_lines.append(line)
    if not attachment_lines:
        attachment_lines = ["- 未提供附件解析摘要"]

    evidence_lines = [
        f"- {item.evidence_id} | {item.claim} → {item.conclusion}"
        for item in context_pack.evidence_chain
    ] or ["- 本阶段尚未生成 evidence_chain"]

    citation_marker_section = "（未启用引用系统）"
    if context_pack.citation_registry is not None:
        citation_marker_section = context_pack.citation_registry.build_marker_list()

    return (
        "【统一生成上下文包】\n"
        f"- module_key：{context_pack.module_key}\n"
        f"- request_id：{context_pack.request_id}\n"
        f"- chapter_id：{chapter_id}\n"
        f"- dpia_required：{diagnosis.get('dpia_required', '未评估')}\n"
        f"- prior_consultation_possible：{diagnosis.get('prior_consultation_possible', '未评估')}\n"
        f"- risk_summary：{context_pack.risk_summary or {}}\n"
        "\n【项目事实与诊断事实】\n"
        + ("\n".join(fact_lines) or "- 未提供")
        + "\n\n【法规依据（使用 source_id 作为 rule_ref）】\n"
        + "\n".join(regulation_lines)
        + "\n\n【本章节相关问题清单】\n"
        + "\n".join(issue_lines)
        + "\n\n【附件解析摘要】\n"
        + "\n".join(attachment_lines)
        + "\n\n【证据链】\n"
        + "\n".join(evidence_lines)
        + "\n\n【法规绑定（legal_grounding）】\n"
        + "\n".join(grounding_lines)
        + "\n\n【可引用法规依据】\n"
        + citation_marker_section
        + "\n\n【表达策略（writing_strategy）】\n"
        + "\n".join(strategy_lines)
        + f"\n\n【全局禁用表达】\n{', '.join(global_forbidden) if global_forbidden else '无'}"
    )


class DPIAChapterGenerator:
    """Generate 7 DPIA draft chapters aligned with ICO DPIA template and GDPR Art 35."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client

    @staticmethod
    def chapter_keys() -> list[str]:
        return list(DPIA_CHAPTER_KEYS)

    def generate(
        self,
        context_pack: GenerationContextPack,
    ) -> list[DPIAChapterContent]:
        citation_keys = [
            f"{item.get('title', '')} {item.get('article', '')}"
            for item in context_pack.regulations[:5]
        ]

        chapters: list[DPIAChapterContent] = []
        for idx, chapter_id in enumerate(DPIA_CHAPTER_KEYS, start=1):
            chapter_title = DPIA_CHAPTER_ID_TO_TITLE[chapter_id]
            chapter_instruction = _CHAPTER_PROMPTS.get(chapter_id, "")
            context_block = build_context_block_from_pack(context_pack, chapter_id)
            citation_registry = context_pack.citation_registry
            content = self._generate_chapter(
                chapter_title, chapter_instruction, context_block, citation_keys, citation_registry
            )
            chapters.append(
                DPIAChapterContent(
                    chapter_no=idx,
                    title=chapter_title,
                    content=content,
                    citations=citation_keys,
                    risk_level="medium",
                )
            )
        return chapters

    def _generate_chapter(
        self,
        title: str,
        instruction: str,
        context: str,
        citations: list[str] | None = None,
        citation_registry: object = None,
    ) -> str:
        if self.llm and self.llm.enabled:
            user_prompt = (
                f"{instruction}\n\n{context}\n\n"
                f"{_STRICT_CONSTRAINT}\n\n"
                "请直接输出章节正文，格式为结构化段落，无需重复章节标题。"
            )
            raw = self.llm.chat(
                system=_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.2,
                max_tokens=1000,
            )
            if citation_registry is not None:
                return convert_citation_markers(raw, citation_registry)
            return ensure_paragraph_citations(raw, citations)
        return f"（{title}：LLM未配置，此处为占位内容）"
