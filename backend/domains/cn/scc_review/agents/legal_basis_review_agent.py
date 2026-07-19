"""P1 Agent 5: LegalBasisReviewAgent — review whether the user's legal basis argument holds water.

Solves: system accepts user's claimed legal basis without scrutiny, but test cases show:
  1. "Personalized service is necessary for contract performance" — may be too broad
  2. "EU certification requirement is a legal obligation" — questionable under Chinese law
  3. "HR management necessity" — may lack employee handbook and collective agreement evidence
  4. "Consent obtained" — may lack complete batch consent records

Reference: docs/archive/design-provenance/认证标准合同路径.md Section 3
"""

from __future__ import annotations

from backend.domains.cn.scc_review.agents import SCCAgentBase
from backend.domains.cn.scc_review.schema import LegalBasis, LegalBasisReviewItem


class LegalBasisReviewAgent(SCCAgentBase):
    agent_name = "cn_scc_legal_basis_review"
    max_tokens = 800

    def run(
        self,
        legal_basis_list: list[str],
        transfer_purpose: str,
        user_argument: str = "",
        contract_summary: str = "",
        privacy_policy_summary: str = "",
        employee_handbook_summary: str = "",
        collective_agreement_summary: str = "",
        consent_record_summary: str = "",
    ) -> list[dict]:
        """Review each legal basis and assess its evidentiary strength.

        Returns one review item per legal basis claimed.
        """
        if not legal_basis_list:
            return [{
                "legal_basis": "未提供",
                "status": "not_recommended",
                "reason": "未声明任何合法性基础，报告无法生成合规论证",
                "recommended_adjustment": "请明确选择至少一项合法性基础",
                "required_evidence": [],
                "evidence_found": [],
                "evidence_missing": ["合法性基础声明"],
            }]

        if not self.enabled:
            return [_rule_based_legal_basis_review(
                basis, transfer_purpose, user_argument,
                contract_summary, privacy_policy_summary,
                employee_handbook_summary, collective_agreement_summary,
                consent_record_summary,
            ) for basis in legal_basis_list]

        results = []
        for basis in legal_basis_list:
            prompt = self._build_prompt(
                basis=basis,
                transfer_purpose=transfer_purpose,
                user_argument=user_argument,
                contract_summary=contract_summary,
                privacy_policy_summary=privacy_policy_summary,
                employee_handbook_summary=employee_handbook_summary,
                collective_agreement_summary=collective_agreement_summary,
                consent_record_summary=consent_record_summary,
            )
            result = self._call_llm(prompt)
            if result is None:
                result = _rule_based_legal_basis_review(
                    basis, transfer_purpose, user_argument,
                    contract_summary, privacy_policy_summary,
                    employee_handbook_summary, collective_agreement_summary,
                    consent_record_summary,
                )
            result.setdefault("legal_basis", basis)
            result.setdefault("status", "weak")
            result.setdefault("reason", "")
            result.setdefault("recommended_adjustment", "")
            result.setdefault("required_evidence", [])
            result.setdefault("evidence_found", [])
            result.setdefault("evidence_missing", [])
            results.append(result)

        return results

    def _build_prompt(
        self,
        basis: str,
        transfer_purpose: str,
        user_argument: str,
        contract_summary: str,
        privacy_policy_summary: str,
        employee_handbook_summary: str,
        collective_agreement_summary: str,
        consent_record_summary: str,
    ) -> str:
        return f"""Review the legal basis "{basis}" for cross-border data transfer under Chinese PIPL.

CONTEXT:
- Transfer Purpose: {transfer_purpose}
- User's Argument: {user_argument[:500] if user_argument else "未提供论证"}
- Contract Summary: {contract_summary[:300] if contract_summary else "未提供"}
- Privacy Policy Summary: {privacy_policy_summary[:300] if privacy_policy_summary else "未提供"}
- Employee Handbook Summary: {employee_handbook_summary[:300] if employee_handbook_summary else "未提供"}
- Collective Agreement Summary: {collective_agreement_summary[:300] if collective_agreement_summary else "未提供"}
- Consent Record Summary: {consent_record_summary[:300] if consent_record_summary else "未提供"}

LEGAL BASIS EVIDENCE REQUIREMENTS:
- "consent" (同意): Must have notice content, recipient name, transfer purpose, withdrawal mechanism, and batch consent records
- "contract_necessity" (合同所必需): Must demonstrate the transfer is necessary for the core obligation of the contract, not merely "helpful" or "for improved experience"
- "hr_management" (人力资源管理所必需): Must have employee handbook AND collective agreement with explicit data export clauses, formulated through democratic procedures
- "legal_obligation" (法定义务): Must cite specific legal provisions that mandate the transfer. EU law requirements are generally NOT Chinese legal obligations
- "vital_interest" (紧急保护): Must demonstrate imminent threat to life, health, or property of natural persons

Return JSON:
{{
  "legal_basis": "{basis}",
  "status": "supported" | "weak" | "insufficient_evidence" | "not_recommended",
  "reason": "<1-2 sentences explaining the assessment>",
  "recommended_adjustment": "<concrete action to strengthen or switch legal basis>",
  "required_evidence": ["evidence type 1", "evidence type 2"],
  "evidence_found": ["evidence actually present"],
  "evidence_missing": ["missing evidence"]
}}

Key pitfalls to detect:
- "Personalized marketing" labeled as "contract necessity" → likely WEAK, it's for commercial purposes
- EU regulation cited as Chinese "legal obligation" → NOT_RECOMMENDED, this is concept confusion
- HR management claim without employee handbook → INSUFFICIENT_EVIDENCE
- Single screenshot as proof of consent for massive user base → INSUFFICIENT_EVIDENCE"""


def _rule_based_legal_basis_review(
    basis: str,
    transfer_purpose: str = "",
    user_argument: str = "",
    contract_summary: str = "",
    privacy_policy_summary: str = "",
    employee_handbook_summary: str = "",
    collective_agreement_summary: str = "",
    consent_record_summary: str = "",
) -> dict:
    """Fallback rule-based legal basis review."""
    required_evidence: list[str] = []
    evidence_found: list[str] = []
    evidence_missing: list[str] = []

    if basis == "consent" or basis == LegalBasis.consent.value:
        required_evidence = ["告知内容", "接收方名称和联系方式", "出境目的", "撤回同意的机制", "批量同意记录"]
        if consent_record_summary:
            evidence_found.append("同意记录摘要已提供")
        else:
            evidence_missing.append("批量同意记录")
        if privacy_policy_summary:
            evidence_found.append("隐私政策摘要已提供")
        else:
            evidence_missing.append("隐私政策/告知书")
        status = "supported" if len(evidence_found) >= 2 else "insufficient_evidence" if evidence_found else "not_recommended"
        reason = "同意作为合法性基础需要完整的告知-同意链路证据" if evidence_missing else "已提供基本同意证据，完整性需核实"

    elif basis == "contract_necessity" or basis == LegalBasis.contract_necessity.value:
        required_evidence = ["合同主给付义务条款", "出境必要性论证", "不可替代性说明"]
        if contract_summary:
            evidence_found.append("合同摘要已提供")
        else:
            evidence_missing.append("合同条款")
        purpose_lower = transfer_purpose.lower()
        weak_purposes = ["营销", "marketing", "个性化", "personalized", "推荐", "recommendation", "体验", "experience"]
        if any(w in purpose_lower for w in weak_purposes):
            reason = "出境目的涉及营销/个性化服务，可能不被认定为'合同所必需'的核心履行行为"
            status = "weak"
        else:
            status = "supported" if evidence_found else "insufficient_evidence"
            reason = "需确认出境是否为合同主给付义务所必需"

    elif basis == "hr_management" or basis == LegalBasis.hr_management.value:
        required_evidence = ["员工手册（含数据出境条款）", "集体合同（含数据出境条款）", "民主程序制定证明", "确需性说明"]
        if employee_handbook_summary:
            evidence_found.append("员工手册摘要已提供")
        else:
            evidence_missing.append("员工手册")
        if collective_agreement_summary:
            evidence_found.append("集体合同摘要已提供")
        else:
            evidence_missing.append("集体合同")
        status = "supported" if len(evidence_found) >= 2 else "insufficient_evidence" if evidence_found else "not_recommended"
        reason = "人力资源管理豁免需要制度文件明确写入个人信息出境条款"

    elif basis == "legal_obligation" or basis == LegalBasis.legal_obligation.value:
        required_evidence = ["具体法律条款引用", "适用主体确认", "强制性要求证明"]
        if "欧盟" in user_argument or "EU" in user_argument.upper() or "GDPR" in user_argument.upper():
            reason = "欧盟法律要求不构成中国《个人信息保护法》下的'法定义务'，建议改为'合同所必需'或'同意'"
            status = "not_recommended"
        else:
            evidence_missing.append("具体法律条款未提供")
            status = "insufficient_evidence"
            reason = "需提供具体中国法律条款证明出境为法定义务"

    elif basis == "vital_interest" or basis == LegalBasis.vital_interest.value:
        required_evidence = ["紧急情况说明", "自然人生命健康财产受威胁的证明"]
        evidence_missing.append("紧急情况证明材料")
        status = "insufficient_evidence"
        reason = "紧急保护自然人生命健康财产属于狭窄例外，适用场景极为有限"

    else:
        required_evidence = ["合法性基础说明"]
        status = "not_recommended"
        reason = f"'{basis}'不是《个人信息保护法》明确规定的合法性基础类型"

    return {
        "legal_basis": basis,
        "status": status,
        "reason": reason,
        "recommended_adjustment": _recommend_adjustment(basis, evidence_missing),
        "required_evidence": required_evidence,
        "evidence_found": evidence_found,
        "evidence_missing": evidence_missing,
    }


def _recommend_adjustment(basis: str, evidence_missing: list[str]) -> str:
    if not evidence_missing:
        return "当前论证基本充分，建议补充详细说明"
    missing_str = "、".join(evidence_missing[:3])
    return f"建议补充{missing_str}，或考虑切换至论证更充分的合法性基础"
