from __future__ import annotations

from backend.common.llm.client import LLMClient
from backend.common.llm.postprocess import convert_citation_markers, ensure_paragraph_citations, strip_markdown_inline
from backend.common.render.summary import attach_citations
from backend.common.risk.scoring import risk_level
from backend.common.workflow import GenerationContextPack
from backend.domains.cn.security_assessment.schema import ChapterContent, CompanyProfile, RegulationHit

_SYSTEM_PROMPT = (
    "你是一名专注于中国数据跨境合规的资深律师，深度掌握《个人信息保护法》《数据安全法》"
    "《数据出境安全评估办法》《数据出境安全评估申报指南（第三版）》等法规。"
    "请严格按照《数据出境风险自评估报告》的行文规范，用专业、严谨的中文撰写报告章节内容。"
    "每章节结构清晰、有据可查，避免空话套话，直接针对企业实际情况分析。"
)

_STRICT_CONSTRAINT = (
    "写作约束：仅使用上下文提供的事实与法规条文，不得新增行业、国家/地区、主体、规模或场景。"
    "若上下文缺失，请写「未提供」。如需推测，请明确标注【推测】。"
    "每个风险判断必须引用上下文中的 issue_id 或法规 citation。"
    "对材料缺失只能写「需补充/待补充」，不得假设材料已经具备。"
    "\n\n引用约束（必须遵守）："
    "\n- 下方【可引用法规依据】提供了可用依据，每条格式为 {{CIT-xxx}} = 法规名 第X条"
    "\n- 需要引用法规时，在句末使用 {{CIT-xxx}} 标记"
    "\n- 禁止使用其他引用格式，禁止编造不在列表中的法规依据"
    "\n- 一个观点可引用多条：{{CIT-xxx}}{{CIT-yyy}}"
    "\n- 若无可引用，写「【依据：未检索到】」"
    "\n\n表达策略硬约束（必须遵守）："
    "\n1. 对外报告只能使用各 issue 的 external_expression 表述，不得使用 internal_expression。"
    "\n2. 不得在报告中出现【全局禁用表达】中列出的任何措辞或近义表述。"
    "\n3. 对于材料缺失/证据不足的 issue，采用审慎保守表述，不得作出正面承诺或确定性结论。"
    "\n4. user_claim_only 类型的事实（标注 evidence_status=user_claim_only）不得作为外部正面结论的唯一依据。"
)

_CHAPTER_PROMPTS: dict[str, str] = {
    "出境活动概述": (
        "请根据以下企业信息，撰写《数据出境风险自评估报告》第一章「出境活动概述」，"
        "包含：(1)企业基本情况；(2)数据出境业务背景；(3)出境活动的必要性说明。"
    ),
    "数据类型与规模": (
        "请根据以下企业信息，撰写第二章「数据类型与规模」，"
        "包含：(1)出境个人信息的具体类型（普通/敏感）及字段清单；"
        "(2)累计出境规模（人数/条数）；(3)是否触发重要数据认定，并说明依据。"
    ),
    "出境必要性与合法性基础": (
        "请根据以下企业信息，撰写第三章「出境必要性与合法性基础」，"
        "包含：(1)业务必要性论证（为什么必须出境，而非境内处理）；"
        "(2)合法性基础（《个保法》第13条、第38条适用情形）；"
        "(3)是否已获取个人信息主体的单独同意（《个保法》第39条）。"
    ),
    "境外接收方保障能力": (
        "请根据以下企业信息，撰写第四章「境外接收方保障能力评估」，"
        "包含：(1)接收方基本情况（名称、国家/地区、法律地位）；"
        "(2)接收方所在地数据保护法律环境分析；"
        "(3)接收方已建立的个人信息保护制度和技术措施；"
        "(4)接收方处理个人信息的目的、方式、范围是否超出合同约定。"
    ),
    "个人信息权益影响分析": (
        "请根据以下企业信息，撰写第五章「个人信息权益影响分析」，"
        "包含：(1)数据主体知情同意权的保障情况；"
        "(2)数据主体查阅、更正、删除、转移等权利的行使途径；"
        "(3)数据出境对数据主体权益可能造成的影响及风险等级（高/中/低）。"
    ),
    "安全措施与传输机制": (
        "请根据以下企业信息，撰写第六章「安全措施与传输机制」，"
        "包含：(1)传输通道加密技术（TLS/HTTPS/专线等）；"
        "(2)访问控制与身份验证机制；"
        "(3)数据最小化和去标识化措施；"
        "(4)与接收方签订的数据处理协议/标准合同的主要条款；"
        "(5)安全事件应急响应预案。"
    ),
    "剩余风险与整改建议": (
        "请根据以下企业信息，撰写第七章「剩余风险识别与整改建议」，"
        "包含：(1)列举已识别的合规风险点（至少3项）；"
        "(2)每项风险的成因、可能影响及风险等级；"
        "(3)具体整改措施和时间表建议；"
        "(4)法规依据引用。"
    ),
    "综合评估结论": (
        "请根据以下企业信息，撰写第八章「综合评估结论」，"
        "包含：(1)总体合规评级（高风险/中风险/低风险）；"
        "(2)核心结论摘要（不超过150字）；"
        "(3)申报建议（是否建议提交安全评估申报，注意事项）；"
        "(4)有效期说明（通常为2年，如业务或法律环境重大变化须重新评估）。"
    ),
}

ASSESSMENT_CHAPTER_KEYS: dict[str, str] = {
    "出境活动概述": "overview",
    "数据类型与规模": "data_scope",
    "出境必要性与合法性基础": "necessity_legal_basis",
    "境外接收方保障能力": "recipient_capability",
    "个人信息权益影响分析": "rights_impact",
    "安全措施与传输机制": "security_measures",
    "剩余风险与整改建议": "risk_remediation",
    "综合评估结论": "conclusion",
}


def _build_context_block(profile: CompanyProfile, hits: list[RegulationHit], level: str) -> str:
    reg_snippet = "\n".join(
        f"- {h.title} {h.article}：{h.snippet[:120]}" for h in hits[:5]
    ) or "（暂无检索到相关法条）"
    return (
        f"【企业基本信息】\n"
        f"- 企业名称：{profile.company_name}\n"
        f"- 行业：{profile.industry or '未填写'}\n"
        f"- 是否CIIO：{'是' if profile.is_ciio else '否'}\n"
        f"- 是否含重要数据：{'是' if profile.contains_important_data else '否'}\n"
        f"- 普通个人信息出境人数：{profile.pii_count:,}人\n"
        f"- 敏感个人信息出境人数：{profile.spi_count:,}人\n"
        f"- 出境目的：{profile.transfer_purpose}\n"
        f"- 境外接收方国家/地区：{profile.receiver_country}\n"
        f"- 整体风险等级：{level}\n"
        f"\n【相关法规条文】\n{reg_snippet}\n"
    )


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
    # Try to use per-section pack from generation_basis_pack first
    section_pack = None
    if context_pack.generation_basis_pack:
        section_packs = context_pack.generation_basis_pack.get("section_packs", [])
        for sp in section_packs:
            if sp.get("section_id") == chapter_id:
                section_pack = sp
                break

    diagnosis = context_pack.diagnosis_result or {}

    if section_pack:
        # Use per-section filtered data from generation_basis_pack
        fact_lines = [
            f"- {fact.get('field_path', fact.get('fact_id', ''))}：{_format_fact_value(fact.get('value'))}"
            for fact in section_pack.get("confirmed_facts", [])
        ] or ["- 本章节无确认事实"]
        regulation_lines = [
            "- {rule_id} | {title}{article}：{snippet}".format(
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
            (
                f"- {issue.issue_id} | {issue.severity} | {issue.title}："
                f"{issue.description}；建议：{issue.recommended_action}"
            )
            for issue in matched_issues
        ] or ["- 未识别到与本章节直接相关的问题项"]

        # Writing strategies from section pack
        chapter_issue_ids = {issue.issue_id for issue in matched_issues}
        ws_items = section_pack.get("writing_strategies", [])
        strategy_lines = [
            (
                f"- {s.get('issue_id', '')} | external_expression: {s.get('external_expression', '')}"
                f" | forbidden: {', '.join(s.get('forbidden_expressions', [])[:3])}"
            )
            for s in ws_items if s.get("issue_id") in chapter_issue_ids
        ] or ["- 本章节无特定表达策略约束"]
        global_forbidden: list[str] = (
            context_pack.writing_strategy.get("global_forbidden_expressions", [])
            if context_pack.writing_strategy else []
        )

        # Legal grounding from section pack
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
        # Fallback: build from global context_pack fields
        fact_lines = [
            f"- {fact.field_path or fact.fact_id}：{_format_fact_value(fact.normalized_value)}"
            for fact in context_pack.facts
            if fact.source_type in {"schema", "diagnosis"}
        ]
        regulation_lines = [
            "- {source_id} | {title}{article}：{snippet}".format(
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
            (
                f"- {issue.issue_id} | {issue.severity} | {issue.title}："
                f"{issue.description}；建议：{issue.recommended_action}"
            )
            for issue in matched_issues
        ] or ["- 未识别到与本章节直接相关的问题项"]

        # Fallback writing strategy
        strategy_lines: list[str] = []
        global_forbidden: list[str] = []
        if context_pack.writing_strategy:
            global_forbidden = context_pack.writing_strategy.get("global_forbidden_expressions", [])
            strategies = context_pack.writing_strategy.get("strategies", [])
            chapter_issue_ids = {issue.issue_id for issue in matched_issues}
            chapter_strategies = [
                s for s in strategies
                if s.get("issue_id") in chapter_issue_ids
            ]
            strategy_lines = [
                (
                    f"- {s['issue_id']} | external_expression: {s.get('external_expression', '')}"
                    f" | forbidden: {', '.join(s.get('forbidden_expressions', [])[:3])}"
                )
                for s in chapter_strategies
            ] or ["- 本章节无特定表达策略约束"]
        else:
            strategy_lines = ["- 未启用表达策略约束"]

        # Fallback legal grounding
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
        attachment_lines = ["- 未提供附件解析摘要；如存在材料缺失，应写明需补充。"]

    evidence_lines = [
        f"- {item.evidence_id} | {item.claim} → {item.conclusion}"
        for item in context_pack.evidence_chain
    ] or ["- 本阶段尚未生成 evidence_chain"]

    reasoning_lines = [
        (
            f"- {item.get('target', '')} | 事实状态: {item.get('fact_status', '')} "
            f"| 风险: {item.get('legal_risk', '')} "
            f"| 对外表达: {item.get('correct_expression', '')}"
        )
        for item in (context_pack.compliance_reasoning or [])[:6]
    ] or ["- 本阶段尚未生成规则分析结论"]

    # Citation marker list for LLM
    citation_marker_section = "（未启用引用系统）"
    if context_pack.citation_registry is not None:
        citation_marker_section = context_pack.citation_registry.build_marker_list()

    return (
        "【统一生成上下文包】\n"
        f"- module_key：{context_pack.module_key}\n"
        f"- request_id：{context_pack.request_id}\n"
        f"- chapter_id：{chapter_id}\n"
        f"- recommended_path：{diagnosis.get('recommended_path', '未提供')}\n"
        f"- path_warning：{context_pack.path_warning or '无'}\n"
        f"- risk_summary：{context_pack.risk_summary or {}}\n"
        "\n【企业事实与诊断事实】\n"
        + ("\n".join(fact_lines) or "- 未提供")
        + "\n\n【法规依据（使用 source_id 作为 rule_ref）】\n"
        + "\n".join(regulation_lines)
        + "\n\n【本章节相关问题清单】\n"
        + "\n".join(issue_lines)
        + "\n\n【附件解析摘要】\n"
        + "\n".join(attachment_lines)
        + "\n\n【证据链】\n"
        + "\n".join(evidence_lines)
        + "\n\n【规则分析结论（compliance_reasoning）】\n"
        + "\n".join(reasoning_lines)
        + "\n\n【法规绑定（legal_grounding）】\n"
        + "\n".join(grounding_lines)
        + "\n\n【可引用法规依据】\n"
        + citation_marker_section
        + "\n\n【表达策略（writing_strategy）】\n"
        + "\n".join(strategy_lines)
        + f"\n\n【全局禁用表达】\n{', '.join(global_forbidden) if global_forbidden else '无'}"
    )


class AssessmentChapterGenerator:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client

    @staticmethod
    def chapter_keys() -> dict[str, str]:
        return dict(ASSESSMENT_CHAPTER_KEYS)

    def generate(
        self,
        profile: CompanyProfile,
        hits: list[RegulationHit],
        context_pack: GenerationContextPack | None = None,
    ) -> list[ChapterContent]:
        level = risk_level(
            is_ciio=profile.is_ciio,
            contains_important_data=profile.contains_important_data,
            pii_count=profile.pii_count,
            spi_count=profile.spi_count,
        )
        citation_keys = [f"{h.title}{h.article}" for h in hits[:5]]

        chapters: list[ChapterContent] = []
        for idx, (chapter_title, chapter_instruction) in enumerate(
            _CHAPTER_PROMPTS.items(), start=1
        ):
            chapter_id = ASSESSMENT_CHAPTER_KEYS[chapter_title]
            context_block = (
                build_context_block_from_pack(context_pack, chapter_id)
                if context_pack is not None
                else _build_context_block(profile, hits, level)
            )
            citation_registry = context_pack.citation_registry if context_pack else None
            content = self._generate_chapter(
                chapter_title,
                chapter_instruction,
                context_block,
                citation_keys,
                citation_registry,
                profile,
                context_pack,
                chapter_id,
            )
            chapters.append(
                ChapterContent(
                    chapter_no=idx,
                    title=chapter_title,
                    content=content,
                    citations=citation_keys,
                    risk_level=level,
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
        profile: CompanyProfile | None = None,
        context_pack: GenerationContextPack | None = None,
        chapter_id: str | None = None,
    ) -> str:
        if self.llm and self.llm.enabled:
            user_prompt = (
                f"{instruction}\n\n{context}\n\n"
                f"{_STRICT_CONSTRAINT}\n\n"
                "请直接输出章节正文，格式为结构化段落，无需重复章节标题。"
            )
            response = self.llm.chat_with_metadata(
                system=_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.2,
                max_tokens=800,
            )
            raw = str(response.get("content") or "").strip()
            # 剥离 LLM 输出的 markdown 内联格式（**粗体**, `代码` 等）
            # DOCX 渲染器不认识 markdown，保留会变成字面 ** 和 _
            raw = strip_markdown_inline(raw)
            if response.get("fallback") or "LLM服务暂时不可用" in raw:
                return self._build_fallback_chapter(
                    title=title,
                    citations=citations,
                    profile=profile,
                    context_pack=context_pack,
                    chapter_id=chapter_id,
                )
            if citation_registry is not None:
                return convert_citation_markers(raw, citation_registry)
            return ensure_paragraph_citations(raw, citations)
        return self._build_fallback_chapter(
            title=title,
            citations=citations,
            profile=profile,
            context_pack=context_pack,
            chapter_id=chapter_id,
        )

    @staticmethod
    def _build_fallback_chapter(
        *,
        title: str,
        citations: list[str] | None,
        profile: CompanyProfile | None,
        context_pack: GenerationContextPack | None,
        chapter_id: str | None,
    ) -> str:
        if profile is None:
            return attach_citations("当前未获取到企业事实，无法生成章节内容。", citations)

        matched_issues = []
        if context_pack is not None and chapter_id is not None:
            matched_issues = [
                issue for issue in context_pack.issues
                if chapter_id in issue.affects_outputs
            ]
            if not matched_issues:
                matched_issues = [
                    issue for issue in context_pack.issues
                    if issue.severity in {"HIGH", "BLOCKER"}
                ][:3]
        diagnosis = context_pack.diagnosis_result if context_pack else {}
        risk_summary = context_pack.risk_summary if context_pack else {}
        writing_strategy = context_pack.writing_strategy if context_pack else {}
        strategy_by_issue = {
            item.get("issue_id"): item
            for item in (writing_strategy.get("strategies", []) if isinstance(writing_strategy, dict) else [])
            if isinstance(item, dict) and item.get("issue_id")
        }

        issue_text_parts: list[str] = []
        for issue in matched_issues[:3]:
            strategy = strategy_by_issue.get(issue.issue_id, {})
            external_expression = str(strategy.get("external_expression", "")).strip()
            if external_expression:
                issue_text_parts.append(f"{issue.issue_id}（{issue.title}）：{external_expression}")
            else:
                issue_text_parts.append(f"{issue.issue_id}（{issue.title}）：需补充相关事实、证据和整改安排。")
        issue_text = "；".join(issue_text_parts) or "当前未识别到与本章节直接冲突的高风险问题，但仍需结合申报材料进一步人工复核。"
        high_issue_list = [
            issue for issue in (context_pack.issues if context_pack else [])
            if issue.severity in {"HIGH", "BLOCKER"}
        ]
        high_issue_summary = "；".join(
            f"{issue.issue_id}（{issue.title}）"
            for issue in high_issue_list[:6]
        ) or "当前未识别到HIGH/BLOCKER等级问题。"

        paragraphs: dict[str, list[str]] = {
            "出境活动概述": [
                f"{profile.company_name}属于{profile.industry or '相关'}行业，当前拟将境内收集和产生的数据传输至{profile.receiver_country}，主要目的为{profile.transfer_purpose}。",
                f"结合诊断结果，系统当前推荐路径为{diagnosis.get('recommended_path', '未提供')}，整体风险等级为{risk_summary.get('risk_level', '未提供')}。",
                f"从现有输入看，本次出境活动的核心关注点包括：{issue_text}",
            ],
            "数据类型与规模": [
                f"现有输入显示，拟出境数据至少涉及普通个人信息约{profile.pii_count:,}人、敏感个人信息约{profile.spi_count:,}人。",
                f"企业当前关于重要数据的自我判断为{'涉及' if profile.contains_important_data else '暂未明确涉及'}重要数据；是否CIIO的输入结论为{'是' if profile.is_ciio else '否'}。",
                "如正式申报，需要进一步细化数据字段、数据主体范围、出境频率及统计口径，并补充重要数据识别依据。",
            ],
            "出境必要性与合法性基础": [
                f"企业主张本次出境系为实现{profile.transfer_purpose}所必需，但现有材料仍需进一步说明为何无法通过境内处理替代，以及数据项范围是否已控制在必要最小限度。",
                "如涉及个人信息出境，应结合《个人信息保护法》第十三条、第三十八条、第三十九条等要求补充合法性基础、单独同意及告知留痕材料。",
                f"与本章节直接相关的关注点包括：{issue_text}",
            ],
            "境外接收方保障能力": [
                f"境外接收方所在地区为{profile.receiver_country}。现有输入说明企业已描述部分技术和管理措施，但仍需结合合同、认证、审计报告等材料验证接收方是否具备与出境风险相匹配的保障能力。",
                "重点应核查接收方是否存在超范围处理、再转移安排、访问控制不足以及当地法律环境变化带来的履约风险。",
                f"当前系统识别的相关问题为：{issue_text}",
            ],
            "个人信息权益影响分析": [
                "对于个人信息主体权益影响，现有输入尚不足以支持作出完全正面的外部结论，尤其需要补充单独同意、告知内容、权利响应流程及留痕证据。",
                "若相关材料不完整，报告中应保持审慎表述，仅说明企业已主张采取相应措施，尚待进一步核验。",
                f"相关风险关注点包括：{issue_text}",
            ],
            "安全措施与传输机制": [
                "现有输入已提及若干技术与管理措施，但正式报告仍需说明传输通道、加密方式、访问控制、日志审计、应急响应以及与境外接收方合同约束的具体落地情况。",
                "对外表述时不得将用户主张直接表述为既成事实，应明确哪些措施已有附件支持，哪些仍属于待补充或待核验状态。",
                f"本章节重点问题为：{issue_text}",
            ],
            "剩余风险与整改建议": [
                f"根据当前诊断与问题识别结果，需优先整改或补强的事项包括：{issue_text}",
                "建议围绕重要数据识别依据、数据字段与规模统计口径、合法性基础证明、境外接收方保障能力文件以及持续监督机制逐项补充材料。",
                "在材料未补齐前，报告结论应保持保守，不宜直接形成“完全合规”或“可直接申报通过”的表述。",
            ],
            "综合评估结论": [
                f"综合现有输入，系统当前推荐路径为{diagnosis.get('recommended_path', '未提供')}，风险等级为{risk_summary.get('risk_level', '未提供')}。",
                f"推荐路径的主要理由为：{diagnosis.get('rationale', '未提供')}。",
                f"本次报告必须重点关注的高风险问题包括：{high_issue_summary}。",
                "本报告在当前模型不可用的情况下根据结构化输入、规则判断、问题项和证据链自动生成，可作为内部补料和人工复核的草案，不宜直接作为最终对外法律意见。",
            ],
        }

        body = "\n\n".join(paragraphs.get(title, ["当前章节缺少专门模板，需结合事实进一步补充。"]))
        return attach_citations(body, citations)
