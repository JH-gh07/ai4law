"""DataSecurityAgreementReviewer — specialized checks for
data security / confidentiality agreements."""

from __future__ import annotations

from backend.schemas.review import ClassifiedClause, ReviewIssue
from backend.services.review_service.specialized_reviewers.base_reviewer import (
    BaseSpecializedReviewer,
)


class DataSecurityAgreementReviewer(BaseSpecializedReviewer):
    """Data‑security‑agreement‑specific compliance checks.

    Rules cover:
    - Data classification (PI / SPI / important data distinction)
    - Data processing location disclosure
    - Cross‑border transmission prohibition (unless authorized)
    - Audit / inspection right
    - Security incident notification timeline
    - Data deletion / return / destruction proof
    - Personnel confidentiality and access control
    - Dispute resolution fairness
    """

    document_type = "other"  # covers confidentiality / data security agreements

    def review(
        self, clause: ClassifiedClause, config: dict,
    ) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        text = clause.text
        ct = clause.clause_type.value

        # ── Data classification ──
        if ct == "DATA_PROCESSING_SCOPE" or ct == "OTHER":
            if not any(term in text for term in ["个人信息", "敏感个人信息",
                                                   "重要数据", "个人敏感信息"]):
                issues.append(self._make_issue(
                    clause, "dsa_no_classification",
                    severity="HIGH",
                    title="未区分个人信息/敏感个人信息/重要数据",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="协议未区分个人信息、敏感个人信息和重要数据，对不同级别数据采用无差别的保护措施。",
                    recommendation="建议明确区分数据类别，对不同级别的数据分别约定保护要求和处理限制。",
                ))

        # ── Data processing location ──
        if ct == "CROSS_BORDER_TRANSFER" or ct == "SECURITY_MEASURES":
            if not any(term in text for term in ["存储地点", "处理地点", "服务器.*位置",
                                                   "数据中心", "机房", "境内"]):
                issues.append(self._make_issue(
                    clause, "dsa_no_location",
                    severity="HIGH",
                    title="未约定数据处理地点",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="协议未约定数据处理和存储的具体地点，无法判断是否涉及数据出境。",
                    recommendation="应明确约定数据处理和存储的具体地点（城市/国家），并声明是否允许在境外处理数据。",
                ))

        # ── Unauthorized cross‑border prohibition ──
        if ct == "CROSS_BORDER_TRANSFER":
            if not any(term in text for term in ["未经.*同意.*不得.*境外", "未经.*授权.*不得.*传输",
                                                   "禁止.*未经.*出境", "限制.*跨境"]):
                issues.append(self._make_issue(
                    clause, "dsa_no_cb_prohibition",
                    severity="HIGH",
                    title="缺少未经授权的跨境传输禁止条款",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="尽管协议可能隐含数据应在中国境内处理，但未明确禁止未经授权的跨境传输。",
                    recommendation="应增加明确条款：未经委托方事先书面同意，受托方不得将数据传输至境外或允许境外访问。",
                ))

        # ── Audit right ──
        if ct == "SECURITY_MEASURES" or ct == "LIABILITY":
            if not any(term in text for term in ["审计", "检查权", "核查", "监督",
                                                   "现场.*检查", "合规.*审查"]):
                issues.append(self._make_issue(
                    clause, "dsa_no_audit",
                    severity="MEDIUM",
                    title="缺少审计监督权约定",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="委托方缺乏对受托方数据处理活动的审计和监督权利，无法验证受托方是否遵守协议约定。",
                    recommendation="建议增加审计条款，赋予委托方定期审计和检查受托方数据处理活动的权利。",
                ))

        # ── Security incident timeline ──
        if ct == "INCIDENT_RESPONSE" or ct == "SECURITY_MEASURES":
            if any(term in text for term in ["及时.*通知", "立即.*通知", "通知",
                                               "报告"]) and not any(
                term in text for term in ["72小时", "24小时", "48小时", "小时.*内",
                                           "工作日内", "日内"]
            ):
                issues.append(self._make_issue(
                    clause, "dsa_incident_vague",
                    severity="HIGH",
                    title="安全事件通知时限过于模糊",
                    problem_type="AMBIGUOUS_LANGUAGE",
                    risk_analysis="协议约定发生安全事件时应'及时'或'立即'通知，但缺乏具体时限标准，可能导致通知严重迟延。",
                    recommendation="建议明确安全事件通知的具体时限，如'知悉安全事件后24小时内书面通知'。",
                ))

        # ── Deletion / destruction proof ──
        if ct == "RETENTION_DELETION":
            if not any(term in text for term in ["销毁证明", "删除证明", "返还.*证明",
                                                   "清除.*确认"]):
                issues.append(self._make_issue(
                    clause, "dsa_no_destruction_proof",
                    severity="MEDIUM",
                    title="缺少数据销毁/删除证明机制",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="协议约定到期后应销毁或删除数据，但未要求提供执行证明。",
                    recommendation="应要求受托方在数据销毁或删除后提供书面证明，确认已不可恢复地清除所有副本。",
                ))

        # ── Personnel confidentiality ──
        if ct == "SECURITY_MEASURES":
            if not any(term in text for term in ["人员.*保密", "员工.*保密", "保密.*义务",
                                                   "保密.*协议", "背景.*审查"]):
                issues.append(self._make_issue(
                    clause, "dsa_no_personnel",
                    severity="MEDIUM",
                    title="未约定人员保密和访问控制措施",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="未要求受托方对接触数据的人员进行保密义务约束和背景审查。",
                    recommendation="建议要求受托方确保接触数据的人员签署保密协议，并实施最小权限访问控制。",
                ))

        # ── Dispute resolution fairness (broad type matching after obligation split) ──
        if ct in ("LIABILITY", "CROSS_BORDER_TRANSFER", "OTHER"):
            import re as _re
            if any(_re.search(p, text) for p in [
                r"香港.*管辖|新加坡.*管辖|境外.*管辖",
                r"受托方.*所在地.*法院|乙方.*所在地.*法院|接收方.*所在地.*法院",
                r"境外.*仲裁|外国.*仲裁",
                r"外国.*法院|域外.*法院",
            ]):
                issues.append(self._make_issue(
                    clause, "dsa_unfair_jurisdiction",
                    severity="HIGH",
                    title="争议解决管辖约定可能对委托方不利",
                    problem_type="NON_COMPLIANT",
                    risk_analysis="争议解决约定选择了境外法院管辖或对委托方明显不便的管辖地。",
                    recommendation="建议将争议解决管辖约定修改为委托方所在地有管辖权的法院或双方协商选择的中国内地仲裁机构。",
                ))

        return issues
