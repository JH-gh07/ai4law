"""DPIA issue builder — identifies GDPR compliance issues from facts and evidence.

Based on WP248 high-risk criteria, GDPR Article 35 requirements, and ICO DPIA guidance.
"""

from __future__ import annotations

from typing import Any

from backend.common.workflow import FactItem, IssueItem


def _by_field(facts: list[FactItem]) -> dict[str, FactItem]:
    return {fact.field_path or "": fact for fact in facts}


def _issue(
    issue_id: str,
    title: str,
    description: str,
    category: str,
    severity: str,
    fact_refs: list[str],
    rule_refs: list[str],
    recommended_action: str,
    affects_outputs: list[str],
) -> IssueItem:
    return IssueItem(
        issue_id=issue_id,
        title=title,
        description=description,
        category=category,
        severity=severity,
        fact_refs=fact_refs,
        rule_refs=rule_refs,
        recommended_action=recommended_action,
        affects_outputs=affects_outputs,
    )


def _diagnosis_value(diagnosis_result: object | None, field: str) -> Any:
    if diagnosis_result is None:
        return None
    if isinstance(diagnosis_result, dict):
        return diagnosis_result.get(field)
    return getattr(diagnosis_result, field, None)


def _get_fact_id(field_path: str, field_facts: dict[str, FactItem]) -> str:
    fact = field_facts.get(field_path)
    return fact.fact_id if fact else ""


def _attachment_evidence(attachment_notes: list) -> dict[str, bool]:
    """Scan attachment_notes for structured evidence relevant to DPIA issues."""
    result: dict[str, bool] = {
        "has_data_flow_diagram": False,
        "has_privacy_policy": False,
        "has_algorithm_description": False,
        "has_fairness_audit": False,
        "has_security_assessment": False,
        "has_consent_flows": False,
        "has_dpo_opinion_file": False,
        "has_ropa": False,
        "has_data_inventory": False,
        "has_safeguards_documentation": False,
    }
    for item in attachment_notes:
        if not isinstance(item, dict):
            continue
        atype = item.get("type", "")
        filename = str(item.get("filename", "")).lower()

        if "data_flow" in filename or "流程图" in filename or "data_flow_diagram" in atype:
            result["has_data_flow_diagram"] = True
        if "privacy" in filename or "隐私" in filename or "policy_doc" in atype:
            result["has_privacy_policy"] = True
        if "algorithm" in filename or "算法" in filename:
            result["has_algorithm_description"] = True
        if "fairness" in filename or "公平性" in filename or "audit" in filename:
            result["has_fairness_audit"] = True
        if "security" in filename or "安全" in filename:
            result["has_security_assessment"] = True
        if "consent" in filename or "同意" in filename:
            result["has_consent_flows"] = True
        if "dpo" in filename or "DPO" in filename:
            result["has_dpo_opinion_file"] = True
        if "ropa" in filename or "记录" in filename or "inventory" in filename:
            result["has_ropa"] = True
        if "safeguard" in filename or "保障" in filename or "measure" in filename:
            result["has_safeguards_documentation"] = True

        if atype == "data_inventory":
            result["has_data_inventory"] = True

    return result


def _rule_refs_for_issue(regulation_refs: list[str], diagnosis_result: object | None) -> list[str]:
    diagnosis_refs: list[str] = []
    legal_basis = _diagnosis_value(diagnosis_result, "legal_basis") or []
    if isinstance(legal_basis, list):
        for base in legal_basis:
            diagnosis_refs.append(f"dpia_need:{base}")
    return diagnosis_refs + regulation_refs[:3]


def build_dpia_issues(
    facts: list[FactItem],
    diagnosis_result: object | None,
    regulations: list[Any],
    attachment_notes: list,
) -> list[IssueItem]:
    field_facts = _by_field(facts)
    issues: list[IssueItem] = []
    regulation_refs = [getattr(r, "source_id", str(r)) for r in regulations if getattr(r, "source_id", None)]
    rule_refs = _rule_refs_for_issue(regulation_refs, diagnosis_result)
    evidence = _attachment_evidence(attachment_notes)

    # ── 1. Automated decision making ──
    auto_fact = field_facts.get("dpia.automated_decision_making")
    if auto_fact and auto_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-automated-decision",
            "自动化决策或画像处理",
            "该项目涉及自动化决策或画像，可能对数据主体产生法律效力或类似重大影响。",
            "automated_decision",
            "HIGH",
            [auto_fact.fact_id],
            rule_refs,
            "落实 GDPR Art 22 要求，确保人工干预、表达观点和质疑决策的权利。补充算法可解释性说明。",
            ["need_identification", "processing_description", "necessity_proportionality", "risk_assessment", "mitigation", "signoff"],
        ))

    # ── 2. Profiling risk ──
    goal_fact = field_facts.get("dpia.project_goal")
    profiling_keywords = ["评估", "评分", "排名", "预测", "分类", "画像", "scoring", "ranking", "profiling"]
    if goal_fact and isinstance(goal_fact.normalized_value, str):
        goal_text = goal_fact.normalized_value.lower()
        if any(kw.lower() in goal_text for kw in profiling_keywords):
            issues.append(_issue(
                "DPIA-ISSUE-profiling-risk",
                "画像处理可能影响数据主体权利",
                "项目目标涉及评估、评分或画像处理，可能对数据主体产生重大影响。",
                "profiling",
                "HIGH",
                [goal_fact.fact_id],
                rule_refs,
                "补充画像逻辑说明、数据来源、准确性保障措施和数据主体异议处理机制。",
                ["need_identification", "processing_description", "risk_assessment", "mitigation"],
            ))

    # ── 3. Special category data ──
    sc_fact = field_facts.get("dpia.special_category_data")
    if sc_fact and sc_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-special-category",
            "特殊类别个人数据处理",
            "该项目涉及处理特殊类别个人数据，属于 GDPR Art 9 禁止处理的情形，需满足法定豁免条件。",
            "special_category",
            "HIGH",
            [sc_fact.fact_id],
            rule_refs + ["GDPR Article 9", "GDPR Article 35"],
            "确认特殊类别数据处理的法律依据（明确同意、重大公共利益等），补充 DPIA 中的特殊类别数据保护措施。",
            ["need_identification", "processing_description", "necessity_proportionality", "risk_assessment", "mitigation", "signoff"],
        ))

    # ── 4. Large scale processing ──
    ls_fact = field_facts.get("dpia.large_scale_processing")
    if ls_fact and ls_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-large-scale",
            "大规模处理个人数据",
            "该项目涉及大规模处理个人数据，属于 WP248 定义的高风险处理活动。",
            "large_scale",
            "HIGH",
            [ls_fact.fact_id],
            rule_refs + ["WP248"],
            "补充处理规模统计口径、数据最小化措施和定期审查计划。",
            ["need_identification", "processing_description", "risk_assessment", "mitigation"],
        ))

    # ── 5. Systematic monitoring ──
    sm_fact = field_facts.get("dpia.systematic_monitoring")
    if sm_fact and sm_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-systematic-monitoring",
            "公共区域大规模系统性监控",
            "该项目涉及公共区域的大规模系统性监控，属于 WP248 明确列举的高风险处理活动。",
            "systematic_monitoring",
            "HIGH",
            [sm_fact.fact_id],
            rule_refs + ["WP248"],
            "补充监控的合法性基础、数据保留期限、透明度措施和数据主体异议机制。",
            ["need_identification", "processing_description", "risk_assessment", "mitigation", "signoff"],
        ))

    # ── 6. Data matching ──
    dm_fact = field_facts.get("dpia.data_matching")
    if dm_fact and dm_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-data-matching",
            "数据匹配或重识别风险",
            "该项目涉及多源数据匹配或重识别组合，可能超出原始收集目的。",
            "data_matching",
            "MEDIUM",
            [dm_fact.fact_id],
            rule_refs + ["WP248"],
            "补充数据匹配的合法基础、目的兼容性分析和重识别风险评估。",
            ["processing_description", "necessity_proportionality", "risk_assessment"],
        ))

    # ── 7. New technology ──
    nt_fact = field_facts.get("dpia.new_technology")
    if nt_fact and nt_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-new-technology",
            "使用新技术处理方式",
            "该项目涉及新技术处理方式，需评估其对个人数据保护的影响。",
            "new_technology",
            "MEDIUM",
            [nt_fact.fact_id],
            rule_refs + ["GDPR Article 35(1)"],
            "补充新技术技术说明、隐私风险评估和对数据主体的影响分析。",
            ["need_identification", "processing_description", "risk_assessment", "mitigation"],
        ))

    # ── 8. Vulnerable data subjects ──
    vs_fact = field_facts.get("dpia.vulnerable_data_subjects")
    if vs_fact and vs_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-vulnerable-subjects",
            "处理弱势数据主体数据",
            "该项目涉及弱势群体数据，存在权力不对等，需特别保护。",
            "vulnerable_subjects",
            "HIGH",
            [vs_fact.fact_id],
            rule_refs + ["WP248"],
            "补充弱势数据主体保护措施、影响评估和额外保障机制。",
            ["need_identification", "processing_description", "risk_assessment", "mitigation", "signoff"],
        ))

    # ── 9. Necessity weak ──
    nec_fact = field_facts.get("dpia.necessity_statement")
    nec_text = str(nec_fact.normalized_value) if nec_fact and nec_fact.normalized_value else ""
    if len(nec_text.strip()) < 50:
        issues.append(_issue(
            "DPIA-ISSUE-necessity-weak",
            "处理必要性论证不充分",
            "当前必要性陈述过于简短（<50字符），不足以支撑严格的必要性审查。",
            "necessity_proportionality",
            "HIGH",
            [nec_fact.fact_id] if nec_fact and nec_fact.fact_id else [],
            rule_refs + ["GDPR Article 35(7)(b)", "GDPR Article 5"],
            "补充详细的必要性论证，说明为何必须处理该个人数据、为何无法以更少侵入性的方式实现目的。",
            ["necessity_proportionality", "risk_assessment"],
        ))

    # ── 10. Proportionality weak ──
    prop_fact = field_facts.get("dpia.proportionality_statement")
    prop_text = str(prop_fact.normalized_value) if prop_fact and prop_fact.normalized_value else ""
    if len(prop_text.strip()) < 50:
        issues.append(_issue(
            "DPIA-ISSUE-proportionality-weak",
            "相称性分析不充分",
            "当前相称性陈述过于简短（<50字符），未充分论证处理手段与目的的相称性。",
            "necessity_proportionality",
            "MEDIUM",
            [prop_fact.fact_id] if prop_fact and prop_fact.fact_id else [],
            rule_refs + ["GDPR Article 5(c) (data minimisation)"],
            "补充相称性分析，论证处理范围、频率和存储期限与处理目的相称。",
            ["necessity_proportionality", "risk_assessment"],
        ))

    # ── 11. Lawful basis unclear ──
    lb_fact = field_facts.get("dpia.lawful_basis")
    lb_value = lb_fact.normalized_value if lb_fact else None
    if not lb_value or (isinstance(lb_value, list) and len(lb_value) == 0):
        issues.append(_issue(
            "DPIA-ISSUE-lawful-basis-unclear",
            "处理合法性基础不明确",
            "未提供清晰的处理合法性基础，无法充分论证处理的合规性。",
            "lawful_basis",
            "HIGH",
            [lb_fact.fact_id] if lb_fact and lb_fact.fact_id else [],
            rule_refs + ["GDPR Article 6"],
            "明确列示该处理活动所依赖的合法性基础（GDPR Art 6(1)）。",
            ["necessity_proportionality", "signoff"],
        ))

    # ── 12. Consent not freely given ──
    sc_types_fact = field_facts.get("dpia.special_category_types")
    sc_types = sc_types_fact.normalized_value if sc_types_fact else []
    if isinstance(sc_types, list) and any(t in str(sc_types).lower() for t in ("健康", "health", "医疗", "medical")):
        consent_risk = True
    else:
        consent_risk = False
    if consent_risk:
        issues.append(_issue(
            "DPIA-ISSUE-consent-not-free",
            "健康数据场景下同意非自由给予的风险",
            "在涉及健康数据的雇佣或保险场景中，由于权力不对等，数据主体的同意可能并非自由给予。",
            "lawful_basis",
            "HIGH",
            [sc_fact.fact_id] if sc_fact and sc_fact.fact_id else [],
            rule_refs + ["GDPR Article 9(2)", "GDPR Article 7"],
            "评估同意是否为自由给予。在雇佣或保险等不对等关系中，考虑是否应依赖其他合法性基础而非同意。",
            ["necessity_proportionality", "risk_assessment", "signoff"],
        ))

    # ── 13. Transparency gap ──
    trans_fact = field_facts.get("dpia.transparency_information")
    trans_text = str(trans_fact.normalized_value) if trans_fact and trans_fact.normalized_value else ""
    if len(trans_text.strip()) < 50:
        issues.append(_issue(
            "DPIA-ISSUE-transparency-gap",
            "透明度信息不足",
            "当前透明度说明过短（<50字符），可能不足以满足 GDPR Art 13/14 的告知要求。",
            "transparency",
            "MEDIUM",
            [trans_fact.fact_id] if trans_fact and trans_fact.fact_id else [],
            rule_refs + ["GDPR Article 13", "GDPR Article 14"],
            "补充数据主体告知内容，包括处理目的、法律依据、数据接收方、保留期限和数据主体权利。",
            ["processing_description", "necessity_proportionality"],
        ))

    # ── 14. Discrimination risk ──
    if (auto_fact and auto_fact.normalized_value is True) and (sc_fact and sc_fact.normalized_value is True):
        issues.append(_issue(
            "DPIA-ISSUE-discrimination-risk",
            "自动化决策叠加特殊类别数据的歧视风险",
            "自动化决策与特殊类别数据叠加使用，可能导致歧视性结果或不公平对待。",
            "discrimination",
            "HIGH",
            [auto_fact.fact_id, sc_fact.fact_id],
            rule_refs + ["GDPR Article 22(4)", "GDPR Recital 71"],
            "补充反歧视保障措施、算法公平性审计和定期偏差检测机制。",
            ["risk_assessment", "mitigation", "signoff"],
        ))

    # ── 15. Cross-border risk ──
    cb_fact = field_facts.get("dpia.cross_border_transfer")
    dest_fact = field_facts.get("dpia.transfer_destination")
    if cb_fact and cb_fact.normalized_value is True:
        dest = str(dest_fact.normalized_value).strip() if dest_fact else ""
        has_adequacy = dest.lower() in (
            "eu", "eea", "european union", "european economic area",
            "andorra", "argentina", "canada", "faroe islands", "guernsey",
            "israel", "isle of man", "japan", "jersey", "new zealand",
            "republic of korea", "switzerland", "united kingdom", "uruguay",
        ) if dest else False
        if not has_adequacy:
            issues.append(_issue(
                "DPIA-ISSUE-cross-border-risk",
                "跨境数据传输缺乏充分性认定保障",
                f"数据将传输至 {dest or '未指定国家'}，该国家/地区尚未获得欧盟充分性认定，需额外保障措施。",
                "cross_border",
                "HIGH",
                [cb_fact.fact_id, dest_fact.fact_id] if dest_fact and dest_fact.fact_id else [cb_fact.fact_id],
                rule_refs + ["GDPR Article 44", "GDPR Article 46"],
                "补充传输保障措施（标准合同条款、约束性公司规则、行为准则等），并评估接收方数据保护水平。",
                ["processing_description", "risk_assessment", "mitigation", "signoff"],
            ))

    # ── 16. Mitigation gap ──
    risk_count = len([f for f in facts if f.field_path and f.field_path.startswith("dpia.identified_risks.")])
    mtg_count = len([f for f in facts if f.field_path and f.field_path.startswith("dpia.mitigation_measures.")])
    if risk_count > 0 and mtg_count == 0:
        issues.append(_issue(
            "DPIA-ISSUE-mitigation-insufficient",
            "缺乏风险缓解措施",
            f"已识别 {risk_count} 项风险但未提供任何缓解措施，无法证明风险已得到充分降低。",
            "mitigation_gap",
            "HIGH",
            [],
            rule_refs + ["GDPR Article 35(7)(d)"],
            "为每项识别的风险补充对应的缓解措施、负责方和实施时间表。",
            ["risk_assessment", "mitigation", "signoff"],
        ))
    elif risk_count > mtg_count:
        issues.append(_issue(
            "DPIA-ISSUE-mitigation-insufficient",
            "缓解措施未能完全覆盖已识别风险",
            f"已识别 {risk_count} 项风险但仅提供 {mtg_count} 项缓解措施，建议逐项对应。",
            "mitigation_gap",
            "MEDIUM",
            [],
            rule_refs + ["GDPR Article 35(7)(d)"],
            "逐项核查每个已识别风险是否有对应的缓解措施。",
            ["mitigation", "signoff"],
        ))

    # ── 17. Prior consultation needed ──
    prior_fact = field_facts.get("dpia_need.prior_consultation_possible")
    if prior_fact and prior_fact.normalized_value is True:
        issues.append(_issue(
            "DPIA-ISSUE-prior-consultation-needed",
            "可能需事先咨询监管机构",
            "存在多项高风险因素，若剩余风险无法充分降低，应依据 GDPR Art 36 进行监管机构事先咨询。",
            "prior_consultation",
            "BLOCKER",
            [prior_fact.fact_id],
            rule_refs + ["GDPR Article 36"],
            "评估剩余风险可接受性。如不可接受，准备事先咨询材料并联系相关监管机构。",
            ["signoff"],
        ))

    # ── 18. DPO opinion missing ──
    dpo_fact = field_facts.get("dpia.dpo_opinion")
    dpo_text = str(dpo_fact.normalized_value).strip() if dpo_fact and dpo_fact.normalized_value else ""
    if not dpo_text:
        issues.append(_issue(
            "DPIA-ISSUE-dpo-opinion-missing",
            "DPO 意见缺失",
            "未提供数据保护官（DPO）的审查意见，DPO 意见是 DPIA 签核的重要组成部分。",
            "documentation",
            "MEDIUM",
            [dpo_fact.fact_id] if dpo_fact and dpo_fact.fact_id else [],
            rule_refs + ["GDPR Article 35(2)", "GDPR Article 39"],
            "请 DPO 审查 DPIA 草案并出具书面意见，包括有条件同意、无条件同意或建议修改。",
            ["signoff"],
        ))

    return issues
