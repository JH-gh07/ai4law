"""US 14117 issue builder — identifies compliance issues from rule engine results."""

from __future__ import annotations

from backend.common.workflow import FactItem, IssueItem
from backend.modules.us_14117.schema import US14117RuleEngineResult


US_14117_CHAPTER_KEYS: dict[str, str] = {
    "总体结论与传输可行性": "overall_conclusion",
    "风险详情与分析": "risk_details",
    "合规措施建议与行动清单": "compliance_actions",
    "附件与持续监控": "attachments_monitoring",
}


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


def build_us_14117_issues(
    facts: list[FactItem],
    rule_engine_result: US14117RuleEngineResult,
    regulations: list[dict],
) -> list[IssueItem]:
    """Generate compliance issues from the rule engine result."""
    by_field = {fact.field_path: fact for fact in facts if fact.field_path}
    rule_refs = [item.get("source_id", "") for item in regulations if item.get("source_id")][:5]
    if not rule_refs:
        rule_refs = ["EO 14117 §100.1", "EO 14117 §100.2", "EO 14117 §100.3"]

    issues: list[IssueItem] = []
    tc = rule_engine_result.transaction_classification
    tl = rule_engine_result.traffic_light

    # ── 1. Prohibited transaction ──
    if tc.get("is_prohibited"):
        fact_refs = [
            f.fact_id for f in facts
            if f.field_path and ("tx.is_prohibited" in f.field_path or "prohibited" in str(f.value).lower())
        ]
        issues.append(_issue(
            "US14117-ISSUE-PROHIBITED-TRANSACTION",
            "禁止交易 (Prohibited Transaction)",
            f"检测到 EO 14117 §100.2 禁止交易: {'; '.join(tc.get('prohibition_reasons', []))}",
            "other",
            "BLOCKER",
            fact_refs or [f.fact_id for f in facts[:1]],
            rule_refs + ["EO 14117 §100.2"],
            "立即停止数据传输，咨询法务团队评估替代方案或豁免申请。",
            ["overall_conclusion", "risk_details", "compliance_actions"],
        ))

    # ── 2. Restricted transaction ──
    if tc.get("is_restricted"):
        fact_refs = [
            f.fact_id for f in facts
            if f.field_path and ("tx.is_restricted" in f.field_path or "restricted" in str(f.value).lower())
        ]
        issues.append(_issue(
            "US14117-ISSUE-RESTRICTED-TRANSACTION",
            "限制性交易 (Restricted Transaction)",
            f"检测到 EO 14117 §100.3 限制性交易: {'; '.join(tc.get('restriction_reasons', []))}",
            "other",
            "HIGH",
            fact_refs or [f.fact_id for f in facts[:1]],
            rule_refs + ["EO 14117 §100.3"],
            "在实施所有必要安全措施并经法务审批后方可继续交易。",
            ["overall_conclusion", "risk_details", "compliance_actions"],
        ))

    # ── 3. Bulk threshold hit ──
    for dc in rule_engine_result.data_classifications:
        if dc.get("threshold_hit") and dc.get("doj_category") != "not_14117_data":
            issues.append(_issue(
                f"US14117-ISSUE-THRESHOLD-{dc['data_item_name'].upper().replace(' ', '-')[:30]}",
                f"批量阈值命中: {dc['data_item_name']}",
                f"数据项 '{dc['data_item_name']}' ({dc['doj_category']}) 的美国人数量 ({dc['us_person_count']}) 超过批量阈值 ({dc['bulk_threshold']})。",
                "data_scope",
                "HIGH",
                [f.fact_id for f in facts if f.field_path and dc['data_item_name'] in f.field_path][:2],
                rule_refs,
                f"评估 {dc['data_item_name']} 的传输必要性，考虑数据最小化、聚合或去标识化。",
                ["risk_details", "compliance_actions"],
            ))

    # ── 4. Covered person detected ──
    for ea in rule_engine_result.entity_assessments:
        if ea.get("is_covered_person"):
            issues.append(_issue(
                f"US14117-ISSUE-COVERED-{ea['entity_name'].upper().replace(' ', '-')[:30]}",
                f"涵盖人员/实体: {ea['entity_name']}",
                f"实体 '{ea['entity_name']}' 被识别为 EO 14117 涵盖人员/实体: {'; '.join(ea.get('covered_person_reasons', []))}",
                "recipient",
                "HIGH",
                [f.fact_id for f in facts if f.field_path and ea['entity_name'] in f.field_path][:2],
                rule_refs + ["EO 14117 §100.1"],
                f"审查与 {ea['entity_name']} 的交易关系，评估是否属于禁止或限制性交易。",
                ["risk_details", "compliance_actions"],
            ))

    # ── 5. Security gaps ──
    sg = rule_engine_result.security_gap_report
    missing = sg.get("missing", [])
    if missing:
        issues.append(_issue(
            "US14117-ISSUE-SECURITY-GAPS",
            "安全措施缺口",
            f"限制性交易缺少 {len(missing)} 项 EO 14117 要求的安全措施: {', '.join(missing[:6])}",
            "security_measure",
            "HIGH",
            [f.fact_id for f in facts if f.field_path and "security_measure" in f.field_path][:2],
            rule_refs + ["EO 14117 §100.3"],
            f"补充缺失的安全措施: {', '.join(missing[:6])}。具体要求参见 EO 14117 实施指南。",
            ["compliance_actions"],
        ))

    # ── 6. Onward transfer risk ──
    onward_fact = by_field.get("request.onward_transfer")
    if onward_fact and onward_fact.normalized_value is True:
        issues.append(_issue(
            "US14117-ISSUE-ONWARD-TRANSFER",
            "再传输风险 (Onward Transfer)",
            "存在 onward transfer / subprocessor 链路，可能导致数据间接流向涵盖人员/受关注国家。",
            "contract",
            "MEDIUM",
            [onward_fact.fact_id],
            rule_refs + ["EO 14117"],
            "补充 onward transfer 清单、再传输审批与审计追踪机制。在合同中加入再传输限制条款。",
            ["risk_details", "compliance_actions"],
        ))

    # ── 7a. Covered person needs review ──
    for ea in rule_engine_result.entity_assessments:
        if ea.get("covered_person_status") == "needs_review":
            issues.append(_issue(
                f"US14117-ISSUE-COVERED-NEEDS-REVIEW-{ea['entity_name'].upper().replace(' ', '-')[:25]}",
                f"涵盖人员状态待确认: {ea['entity_name']}",
                f"实体 '{ea['entity_name']}' 的涵盖人员状态为 'needs_review'，存在受关注国家关联但信息不足以确认。"
                f"缺失信息: {'; '.join(ea.get('missing_information', [])[:3])}",
                "recipient",
                "MEDIUM",
                [f.fact_id for f in facts if f.field_path and ea['entity_name'] in f.field_path][:2],
                rule_refs + ["EO 14117 §100.1"],
                f"补充 {ea['entity_name']} 的尽调材料后重新评估。参见追问清单。",
                ["risk_details", "overall_conclusion"],
            ))

    # ── 7b. Yellow-blocked ──
    if tl.yellow_status == "blocked":
        issues.append(_issue(
            "US14117-ISSUE-YELLOW-BLOCKED",
            "黄灯-整改前禁止推进",
            f"限制性交易存在 {len(tl.missing_security_measures)} 项安全措施缺口，在整改完成前不得继续推进数据传输。",
            "security_measure",
            "HIGH",
            [f.fact_id for f in facts if f.field_path and "security_measure" in f.field_path][:2],
            rule_refs + ["EO 14117 §100.3"],
            f"在90天内完成以下措施整改: {', '.join(tl.missing_security_measures[:6])}。完成后重新提交评估。",
            ["compliance_actions", "overall_conclusion"],
        ))

    # ── 7c. Clarification needed ──
    all_missing_info: list[str] = []
    for ea in rule_engine_result.entity_assessments:
        all_missing_info.extend(ea.get("missing_information", []))
    if all_missing_info or tl.clarification_questions:
        issues.append(_issue(
            "US14117-ISSUE-CLARIFICATION-NEEDED",
            "需补充尽调材料",
            f"评估过程中发现 {len(all_missing_info) + len(tl.clarification_questions)} 项信息缺口，需补充材料后方可作出最终判断。",
            "documentation",
            "MEDIUM",
            [f.fact_id for f in facts[:1]],
            rule_refs,
            "参见报告中的追问清单，补充相关材料后重新提交评估。",
            ["overall_conclusion", "attachments_monitoring"],
        ))

    # ── 8. Data classification uncertain ──
    uncertain = [
        dc for dc in rule_engine_result.data_classifications
        if dc.get("confidence", 1.0) < 0.75
    ]
    if uncertain:
        issues.append(_issue(
            "US14117-ISSUE-DATA-CLASSIFICATION-UNCERTAIN",
            "数据分类置信度不足",
            f"以下数据项的分类置信度低于75%: {', '.join(dc['data_item_name'] for dc in uncertain)}。建议人工复核。",
            "data_scope",
            "MEDIUM",
            [f.fact_id for f in facts if f.field_path and "classification" in f.field_path][:2],
            rule_refs,
            "人工复核不确定的数据项分类，更新 doj_data_category 字段后重新评估。",
            ["risk_details"],
        ))

    # ── 8. No trigger (green) ──
    if not tc.get("is_prohibited") and not tc.get("is_restricted"):
        issues.append(_issue(
            "US14117-ISSUE-NO-TRIGGER",
            "未触发 EO 14117 规则",
            "当前交易不直接触发 EO 14117 §100.2 或 §100.3。建议持续监控并定期复审。",
            "other",
            "LOW",
            [f.fact_id for f in facts if f.field_path and "traffic_light" in f.field_path][:1],
            rule_refs,
            "保持当前合规状态，建立季度复审机制，监控法规更新和接收方变化。",
            ["overall_conclusion"],
        ))

    return issues
