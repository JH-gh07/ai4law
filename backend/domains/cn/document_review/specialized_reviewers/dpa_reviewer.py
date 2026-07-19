"""DpaReviewer — specialized checks for data processing agreements / DPA."""

from __future__ import annotations

from backend.schemas.review import ClassifiedClause, ReviewIssue
from backend.domains.cn.document_review.specialized_reviewers.base_reviewer import (
    BaseSpecializedReviewer,
)


class DpaReviewer(BaseSpecializedReviewer):
    """DPA‑specific compliance checks.

    Rules cover:
    - Role clarity (controller vs processor)
    - Data scope definition
    - Processing purpose / method / scope
    - Data ownership (input vs. output data)
    - Scope limitation (no exceeding agreed processing)
    - Sub‑processor / onward transfer restrictions
    - Security incident notification timeline
    - Data return / deletion / destruction proof
    - Cross‑border processing identification
    - Liability allocation (no shifting legal compliance duty to processor)
    """

    document_type = "dpa"

    def review(
        self, clause: ClassifiedClause, config: dict,
    ) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        text = clause.text
        ct = clause.clause_type.value

        # ── Role clarity ──
        if ct == "ENTRUSTED_PROCESSING":
            if not any(term in text for term in ["委托方", "受托方", "个人信息处理者",
                                                   "数据处理者", "受托处理"]):
                issues.append(self._make_issue(
                    clause, "dpa_role_unclear",
                    severity="HIGH",
                    title="委托方/受托方角色不明确",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="数据处理协议未明确区分委托方（个人信息处理者）和受托方的角色和责任。",
                    recommendation="应在协议开头明确定义委托方和受托方的法律地位和各自职责。",
                ))

        # ── Data scope definition ──
        if ct == "DATA_PROCESSING_SCOPE":
            if not any(term in text for term in ["数据名称", "数据内容", "数据规模",
                                                   "数据来源", "字段"]):
                issues.append(self._make_issue(
                    clause, "dpa_data_scope_vague",
                    severity="MEDIUM",
                    title="数据处理范围未明确数据名称/内容/规模/来源",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="协议未明确委托处理的数据名称、内容、规模和来源，可能导致处理范围争议。",
                    recommendation="应补充数据名称、内容、规模和来源的具体描述。",
                ))

        # ── Data ownership ──
        if ct == "DATA_PROCESSING_SCOPE":
            if not any(term in text for term in ["数据权属", "过程数据", "结果数据",
                                                   "衍生数据", "产出数据"]):
                issues.append(self._make_issue(
                    clause, "dpa_data_ownership",
                    severity="MEDIUM",
                    title="未约定过程数据和结果数据的权属",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="委托处理过程中可能产生过程数据和结果数据，未约定权属可能导致知识产权和数据权属争议。",
                    recommendation="建议明确过程数据、结果数据的权属、使用限制和到期处理方式。",
                ))

        # ── Scope limitation ──
        if ct == "ENTRUSTED_PROCESSING" or ct == "DATA_PROCESSING_SCOPE":
            if not any(term in text for term in ["不得超出", "按照指示", "依指示",
                                                   "未经.*同意.*不得", "限定"]):
                issues.append(self._make_issue(
                    clause, "dpa_no_scope_limit",
                    severity="HIGH",
                    title="未限定受托方不得超出约定范围处理数据",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="未明确受托方仅能按照委托方书面指示处理数据，受托方可能自行决定处理目的和方式。",
                    recommendation="应明确受托方仅能按委托方书面指示处理数据，不得自行决定处理目的和方式。",
                ))

        # ── Sub‑processor restrictions ──
        if ct == "ONWARD_TRANSFER" or ct == "ENTRUSTED_PROCESSING":
            if "再转移" in text or "转委托" in text or "子处理者" in text or "下级处理者" in text:
                if not any(term in text for term in ["书面同意", "事先同意", "通知",
                                                       "同等.*保护", "不低于"]):
                    issues.append(self._make_issue(
                        clause, "dpa_onward_weak",
                        severity="HIGH",
                        title="再转移/转委托限制不足",
                        problem_type="MISSING_REQUIREMENT",
                        risk_analysis="允许转委托但未要求事先书面同意或未要求再转移接收方承担同等保护义务。",
                        recommendation="应要求转委托须获委托方事先书面同意，且再转移接收方需承担不低于受托方的保护义务。",
                    ))

        # ── Security incident timeline ──
        if ct == "INCIDENT_RESPONSE" or ct == "SECURITY_MEASURES":
            if not any(term in text for term in ["72小时", "24小时", "48小时", "立即",
                                                   "小时.*内", "工作日内"]):
                issues.append(self._make_issue(
                    clause, "dpa_no_incident_timeline",
                    severity="HIGH",
                    title="未约定安全事件通知的具体时限",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="协议仅笼统约定发生安全事件时通知，未给出具体通知时限（如72小时内）。",
                    recommendation="建议明确安全事件通知的具体时限，如'知悉后24小时内书面通知'。",
                ))

        # ── Data return / deletion proof ──
        if ct == "RETENTION_DELETION":
            if not any(term in text for term in ["返还", "销毁证明", "删除证明",
                                                   "清除.*证明", "处置.*证明"]):
                issues.append(self._make_issue(
                    clause, "dpa_no_deletion_proof",
                    severity="MEDIUM",
                    title="未约定数据删除/返还的证明机制",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="协议约定委托关系终止后应删除或返还数据，但未要求受托方提供删除/返还的书面证明。",
                    recommendation="应要求受托方在委托关系终止后提供数据删除或返还的书面证明。",
                ))

        # ── Cross‑border identification ──
        if ct == "CROSS_BORDER_TRANSFER":
            if not any(term in text for term in ["安全评估", "标准合同", "保护认证",
                                                   "认证", "评估"]):
                issues.append(self._make_issue(
                    clause, "dpa_no_cb_mechanism",
                    severity="HIGH",
                    title="涉及跨境处理但未说明合法机制",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="协议涉及数据跨境传输，但未说明依据的合法机制（安全评估/标准合同/保护认证）。",
                    recommendation="应明确数据跨境传输的合法机制及已完成的合规步骤。",
                ))

        # ── Liability mis‑allocation ──
        if ct in ("LIABILITY", "CROSS_BORDER_TRANSFER", "ENTRUSTED_PROCESSING", "OTHER"):
            import re as _re
            if any(_re.search(p, text) for p in [
                r"(受托方|乙方).*(负责|完成|承担).*(合规|安全评估|标准合同|保护认证)",
                r"由.*(受托方|乙方).*负责.*(申报|订立|完成)",
            ]):
                issues.append(self._make_issue(
                    clause, "dpa_liability_misalloc",
                    severity="HIGH",
                    title="法定合规责任可能被不当转移至受托方",
                    problem_type="NON_COMPLIANT",
                    risk_analysis="条款将数据出境的法定合规责任（如安全评估申报、标准合同订立）全部或主要转移至受托方。根据《个人信息保护法》，个人信息处理者是合规义务的法定责任主体。",
                    recommendation="应明确委托方作为个人信息处理者的法定合规责任，受托方仅承担协助配合义务。",
                ))

        # ── Standard contract body conflict (DPA may reference SCC) ──
        if any(term in text for term in ["标准合同", "个人信息出境标准合同", "SCC"]):
            if any(term in text for term in ["不一致.*为准", "以.*为准", "优先.*适用",
                                               "优先于", "以本合同为准"]):
                issues.append(self._make_issue(
                    clause, "dpa_scc_priority_conflict",
                    severity="HIGH",
                    title="条款与标准合同正文可能存在优先冲突",
                    problem_type="NON_COMPLIANT",
                    risk_analysis="协议约定自身优先于标准合同正文条款，这可能违反《个人信息出境标准合同办法》关于其他约定不得与标准合同正文冲突的规定。",
                    recommendation="应删除或修改此条款，确保不与标准合同正文冲突并在冲突时以标准合同正文为准。",
                ))

        return issues
