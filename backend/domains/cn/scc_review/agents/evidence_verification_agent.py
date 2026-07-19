"""P1 Agent 4: EvidenceVerificationAgent — verify whether user claims are backed by sufficient evidence.

Solves: the report must not write user claims as confirmed compliance facts.
Instead, the agent assesses whether uploaded materials support each positive claim.

Reference: docs/archive/design-provenance/认证标准合同路径.md Section 5
"""

from __future__ import annotations

from backend.domains.cn.scc_review.agents import SCCAgentBase
from backend.domains.cn.scc_review.schema import EvidenceStrength, EvidenceVerificationItem


class EvidenceVerificationAgent(SCCAgentBase):
    agent_name = "cn_scc_evidence_verification"
    max_tokens = 800

    def run(
        self,
        claims: list[dict],
        uploaded_materials: list[str],
        material_summaries: dict[str, str] | None = None,
    ) -> list[dict]:
        """Verify whether each user claim has sufficient supporting evidence.

        claims: list of {"claim": str, "category": str} — user statements to verify
        uploaded_materials: list of file names/paths the user has provided
        material_summaries: dict of filename → summary text
        """
        if not claims:
            return []

        if not self.enabled:
            return [_rule_based_evidence_check(c, uploaded_materials, material_summaries or {}) for c in claims]

        materials_str = "\n".join(f"- {m}" for m in uploaded_materials) if uploaded_materials else "（未上传材料）"
        summaries_str = ""
        if material_summaries:
            for name, summary in material_summaries.items():
                summaries_str += f"\n{name}: {summary[:200]}"

        claims_str = "\n".join(
            f"{i + 1}. [{c.get('category', '未分类')}] {c['claim']}" for i, c in enumerate(claims)
        )

        prompt = f"""Verify whether each user claim about cross-border data transfer compliance is backed by sufficient evidence.

USER CLAIMS:
{claims_str}

UPLOADED MATERIALS:
{materials_str}

MATERIAL SUMMARIES:
{summaries_str}

TASKS:
For each claim, determine:
1. Evidence Status:
   - "verified_evidence": material clearly and completely supports the claim
   - "documented_evidence": material exists and supports the claim but completeness is uncertain
   - "partial_evidence": some material supports but gaps remain
   - "user_claim_only": no material supports the claim, it's only the user's word

2. Gap Analysis: what specific evidence is missing?
3. Report Strategy: how should the report phrase this?
   - "可以肯定表述" (can assert positively)
   - "只能谨慎表述" (must be cautious)
   - "必须标记为缺失" (must flag as missing)
   - "必须作为高风险项" (must flag as high risk)

Return JSON array:
[
  {{
    "claim": "<the original claim>",
    "evidence_status": "user_claim_only" | "partial_evidence" | "documented_evidence" | "verified_evidence",
    "supporting_material": ["material1", "material2"],
    "gap": "<what's missing, if anything>",
    "report_strategy": "<how to phrase in the report>"
  }}
]

IMPORTANT:
- Be conservative: "user_claim_only" is the default unless evidence is clearly present
- A single screenshot of consent records cannot prove consent for ALL 500,000 users
- Employee handbooks must explicitly mention data export to count as HR exemption evidence
- Business certification (ISO 27001, SOC 2) is NOT the same as Chinese PIPL certification
"""

        result = self._call_llm(prompt)
        if result is None:
            return [_rule_based_evidence_check(c, uploaded_materials, material_summaries or {}) for c in claims]

        if isinstance(result, dict):
            result = [result]
        if not isinstance(result, list):
            return [_rule_based_evidence_check(c, uploaded_materials, material_summaries or {}) for c in claims]

        for item in result:
            item.setdefault("evidence_status", "user_claim_only")
            item.setdefault("supporting_material", [])
            item.setdefault("gap", "")
            item.setdefault("report_strategy", "必须标记为缺失")

        return result


def _rule_based_evidence_check(
    claim: dict,
    uploaded_materials: list[str],
    material_summaries: dict[str, str],
) -> dict:
    """Fallback evidence check based on keyword matching."""
    claim_text = claim.get("claim", "")
    claim_category = claim.get("category", "")
    claim_lower = claim_text.lower()

    evidence_keywords = {
        "consent": ["同意记录", "consent", "同意书", "告知同意", "privacy notice", "隐私政策"],
        "security": ["安全认证", "security cert", "ISO 27001", "等保", "SOC 2", "audit report", "审计报告"],
        "contract": ["合同", "contract", "SCC", "DPA", "agreement", "协议"],
        "employee": ["员工手册", "employee handbook", "集体合同", "collective agreement", "labor", "劳动"],
        "certification": ["认证", "certification", "certificate"],
        "anonymization": ["匿名化", "anonymization", "哈希", "hash", "脱敏"],
        "policy": ["制度", "policy", "制度文件"],
    }

    relevant_keywords = []
    for cat, keywords in evidence_keywords.items():
        if cat in claim_lower or cat in claim_category:
            relevant_keywords.extend(keywords)

    found_materials = []
    all_text = " ".join(uploaded_materials) + " " + " ".join(material_summaries.values())
    all_lower = all_text.lower()

    for kw in relevant_keywords:
        if kw.lower() in all_lower:
            found_materials.append(kw)

    if found_materials:
        return {
            "claim": claim_text,
            "evidence_status": "partial_evidence",
            "supporting_material": found_materials[:3],
            "gap": "需人工确认材料是否完整覆盖全部目标范围",
            "report_strategy": "只能谨慎表述，需注明基于部分样本证据",
        }

    return {
        "claim": claim_text,
        "evidence_status": "user_claim_only",
        "supporting_material": [],
        "gap": f"未在已上传材料中发现支撑'{claim_text}'的证据",
        "report_strategy": "必须标记为缺失，不得写入报告结论",
    }
