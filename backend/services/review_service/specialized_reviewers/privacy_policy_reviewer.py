"""PrivacyPolicyReviewer — specialized checks for privacy policy documents."""

from __future__ import annotations

from backend.schemas.review import ClassifiedClause, ReviewIssue
from backend.services.review_service.specialized_reviewers.base_reviewer import (
    BaseSpecializedReviewer,
)


class PrivacyPolicyReviewer(BaseSpecializedReviewer):
    """Privacy‑policy‑specific compliance checks.

    Additional rules beyond the base rulebook:
    - Minor age threshold (14 years old)
    - Rights request response time (30 days)
    - Contact channel completeness (email + phone + address)
    - Cookie/SDK disclosure
    - Separate consent for sensitive PI
    - Cross‑border legal mechanism disclosure
    """

    document_type = "privacy_policy"

    def review(
        self, clause: ClassifiedClause, config: dict,
    ) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        text = clause.text
        ct = clause.clause_type.value

        # ── Minor protection: age threshold check ──
        if ct == "MINOR_PROTECTION":
            if "14岁" not in text and "十四周岁" not in text:
                issues.append(self._make_issue(
                    clause, "pp_minor_age",
                    severity="MEDIUM",
                    title="未明确未成年人年龄标准（14周岁）",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="处理未成年人信息但未明确14周岁的年龄标准。《个人信息保护法》第31条及《儿童个人信息网络保护规定》要求明确年龄门槛。",
                    recommendation="建议明确说明处理不满14周岁未成年人个人信息的规则，以及如何获取监护人同意。",
                ))

        # ── Rights request: response time ──
        if ct == "RIGHTS_REQUEST":
            if not any(term in text for term in ["30日", "15日", "工作日", "30个工作日", "15个工作日"]):
                issues.append(self._make_issue(
                    clause, "pp_rights_response",
                    severity="MEDIUM",
                    title="未说明权利请求响应时限",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="未承诺响应个人信息主体权利请求的具体时限。依据行业惯例，通常应在15-30个工作日内响应。",
                    recommendation="建议明确权利请求响应时限，例如'我们将在15个工作日内响应您的请求'。",
                ))

        # ── Contact channel completeness ──
        if ct == "CONSENT_NOTICE":
            has_email = bool("@" in text)
            has_phone = bool(any(c in text for c in ["电话", "400", "座机", "热线"]))
            if not has_email and not has_phone:
                issues.append(self._make_issue(
                    clause, "pp_contact_incomplete",
                    severity="MEDIUM",
                    title="联系方式信息不完整",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="隐私政策应提供完整的联系方式（建议含邮箱和电话），以便个人信息主体行使权利或提出投诉。",
                    recommendation="建议补充完整的联系方式，包括电子邮箱和电话号码。",
                ))

        # ── Cookie / SDK disclosure ──
        if ct == "THIRD_PARTY_SHARING":
            if not any(term in text for term in ["Cookie", "SDK", "cookie", "sdk"]):
                issues.append(self._make_issue(
                    clause, "pp_cookie_sdk",
                    severity="LOW",
                    title="未提及Cookie或SDK技术",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="如产品使用Cookie或接入第三方SDK，隐私政策应说明其用途、收集的信息类型和用户控制方式。",
                    recommendation="如适用，建议补充Cookie/SDK使用说明。",
                ))

        # ── Sensitive PI: separate consent ──
        if ct == "SENSITIVE_PI":
            if "单独同意" not in text:
                issues.append(self._make_issue(
                    clause, "pp_spi_consent",
                    severity="HIGH",
                    title="敏感个人信息缺少单独同意机制说明",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="处理敏感个人信息需取得个人信息主体的单独同意。隐私政策应说明如何获取和记录单独同意。",
                    recommendation="应明确说明在收集敏感个人信息前将获取个人信息主体的单独同意。",
                ))

        # ── Cross‑border: legal mechanism ──
        if ct == "CROSS_BORDER_TRANSFER":
            if not any(term in text for term in ["安全评估", "标准合同", "保护认证", "认证"]):
                issues.append(self._make_issue(
                    clause, "pp_cb_mechanism",
                    severity="HIGH",
                    title="未说明数据出境的合法机制",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis="隐私政策中提及数据出境但未说明依据的合法机制（安全评估/标准合同/保护认证）。",
                    recommendation="建议明确说明数据出境所依据的合法机制及其基本情况。",
                ))

        return issues
