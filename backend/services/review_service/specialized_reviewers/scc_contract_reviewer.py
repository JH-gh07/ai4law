"""SccContractReviewer — specialized checks for standard contractual clauses."""

from __future__ import annotations

from backend.schemas.review import ClassifiedClause, ReviewIssue
from backend.services.review_service.specialized_reviewers.base_reviewer import (
    BaseSpecializedReviewer,
)


class SccContractReviewer(BaseSpecializedReviewer):
    """SCC‑specific compliance checks.

    Additional rules:
    - Annex I field completeness (processing purpose, method, scale, categories,
      sensitive PI, overseas third parties, transfer method, retention period,
      storage location)
    - Annex II conflict detection (liability cap, foreign court jurisdiction,
      other agreement priority, suspension of subject rights, weakening of
      recipient obligations)
    - Body text modification detection
    """

    document_type = "scc_contract"

    # ── Annex I required fields ──────────────────────────────────────────
    _ANNEX_I_REQUIRED_FIELDS: list[tuple[str, str, list[str]]] = [
        ("处理目的", "app1_purpose", ["处理目的", "出境目的"]),
        ("处理方式", "app1_method", ["处理方式", "自动化", "分析", "存储"]),
        ("个人信息规模", "app1_scale", ["规模", "数量", "人数", "条数"]),
        ("个人信息种类", "app1_categories", ["种类", "类型", "字段"]),
        ("敏感个人信息种类", "app1_spi", ["敏感个人信息", "敏感数据"]),
        ("境外接收方信息", "app1_recipient", ["境外接收方", "境外.*方", "接收方.*名称"]),
        ("传输方式", "app1_transfer", ["传输方式", "传输途径", "网络传输", "物理介质"]),
        ("保存期限", "app1_retention", ["保存期限", "存储期限", "保留"]),
        ("保存地点", "app1_location", ["保存地点", "存储地点", "服务器", "数据中心"]),
    ]

    # ── Annex II conflict patterns ───────────────────────────────────────
    _ANNEX_II_CONFLICT_CHECKS: list[dict] = [
        {
            "id": "scc_liability_cap",
            "pattern": "责任上限|赔偿上限|最高.*赔偿|责任.*限额",
            "severity": "MEDIUM",
            "title": "责任上限条款可能与标准合同正文冲突",
            "problem_type": "NON_COMPLIANT",
            "risk_analysis": "标准合同附录二不得包含削弱个人信息主体权利的条款。责任上限条款可能不当限制境外接收方的责任。",
            "recommendation": "建议审查责任上限条款是否与标准合同正文一致，确保不削弱对个人信息主体的保护。",
        },
        {
            "id": "scc_foreign_court",
            "pattern": "香港.*法院|新加坡.*法院|美国.*法院|境外.*管辖|域外.*法院|外国.*法院|英国.*法院",
            "severity": "HIGH",
            "title": "争议解决约定为境外法院管辖",
            "problem_type": "NON_COMPLIANT",
            "risk_analysis": "根据《个人信息出境标准合同办法》第五条，争议解决应选择中国内地有管辖权的法院或仲裁机构。",
            "recommendation": "应修改争议解决条款，选择中国内地有管辖权的法院或仲裁机构。",
        },
        {
            "id": "scc_other_agreement_priority",
            "pattern": "其他协议.*优先|优先.*商业.*协议|以.*商业合同.*为准|主协议.*优先",
            "severity": "HIGH",
            "title": "其他协议优先条款可能削弱标准合同约束力",
            "problem_type": "NON_COMPLIANT",
            "risk_analysis": "标准合同正文约定其他约定不得与正文冲突。其他协议优先条款可能导致标准合同条款被架空。",
            "recommendation": "应删除或修改该条款，确保标准合同正文条款优先适用。",
        },
        {
            "id": "scc_suspend_rights",
            "pattern": "暂缓.*请求|暂停.*处理.*请求|延迟.*主体.*权利",
            "severity": "HIGH",
            "title": "暂缓处理主体请求条款可能削弱权利保障",
            "problem_type": "NON_COMPLIANT",
            "risk_analysis": "标准合同要求保障个人信息主体的查阅、更正、删除等权利。暂缓处理条款可能不当限制这些权利。",
            "recommendation": "建议删除或严格限定暂缓处理的条件，确保不实质性地削弱个人信息主体的权利。",
        },
        {
            "id": "scc_weaken_recipient",
            "pattern": "免除.*责任|豁免.*义务|免除.*赔偿",
            "severity": "MEDIUM",
            "title": "可能存在削弱境外接收方义务的条款",
            "problem_type": "NON_COMPLIANT",
            "risk_analysis": "标准合同要求境外接收方承担不低于中国法律规定的个人信息保护义务。免责条款可能削弱这些义务。",
            "recommendation": "建议审查免责条款是否与标准合同要求一致，确保境外接收方的保护义务未被削弱。",
        },
    ]

    def review(
        self, clause: ClassifiedClause, config: dict,
    ) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        text = clause.text
        ct = clause.clause_type.value

        # ── Annex I completeness checks ──
        if clause.is_appendix_content:
            for field_label, check_id, keywords in self._ANNEX_I_REQUIRED_FIELDS:
                if not any(kw in text for kw in keywords):
                    issues.append(self._make_issue(
                        clause, check_id,
                        severity="MEDIUM",
                        title=f"附录一缺少必填字段：{field_label}",
                        problem_type="MISSING_REQUIREMENT",
                        risk_analysis=f"个人信息出境标准合同附录一要求填写{field_label}，当前未检测到该字段。",
                        recommendation=f"请在附录一中补充{field_label}的具体内容。",
                    ))

        # ── Annex II conflict checks ──
        for cc in self._ANNEX_II_CONFLICT_CHECKS:
            try:
                if cc["pattern"] in text:
                    issues.append(self._make_issue(
                        clause, cc["id"],
                        severity=cc["severity"],
                        title=cc["title"],
                        problem_type=cc["problem_type"],
                        risk_analysis=cc["risk_analysis"],
                        recommendation=cc["recommendation"],
                    ))
            except Exception:
                continue

        # ── Body text modification check ──
        if ct == "OTHER" and not clause.is_appendix_content:
            # Check for signs that SCC body text has been modified
            modification_signals = [
                ("删除", "标准合同正文约定不可删除的条款被标记删除"),
                ("修改", "标准合同法条文的修改可能影响合同效力"),
                ("除外", "除外条款可能改变标准合同的适用范围"),
            ]
            for signal, risk in modification_signals:
                if signal in text:
                    issues.append(self._make_issue(
                        clause, f"scc_body_mod_{signal}",
                        severity="HIGH",
                        title=f"标准合同正文疑似被修改（含「{signal}」标识）",
                        problem_type="NON_COMPLIANT",
                        risk_analysis=risk,
                        recommendation="标准合同正文条款不得修改。如需增加约定，应在附录二中另行约定且不得与正文冲突。",
                    ))
                    break

        return issues
