"""L1 Platform base model — Expression safety layer.

This module defines the platform's "writing constitution": rules about what
language may and may not appear in external reports.  Every LLM-generated
sentence in an official-facing document must respect these constraints.

The core insight: there is a fundamental difference between what the system
concludes internally and what it may state in a document that could be
submitted to a regulator or relied upon by a business.
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.common.workflow.facts import EvidenceStatus


# ── Enumerations ──────────────────────────────────────────────────────────

ExpressionStyle = Literal[
    "affirmative",   # "已覆盖……" — only when evidence_status ≥ documented_evidence
    "cautious",      # "用户已说明……但需补充……" — when evidence_status = partial_evidence
    "conditional",   # "若……则……" — when a conclusion depends on an unverified premise
    "deferred",      # "当前材料尚不足以……建议……" — when evidence_status = user_claim_only
]


# ── Core models ───────────────────────────────────────────────────────────

class ExpressionStrategy(BaseModel):
    """Mapping from a factual claim to its permissible external-report phrasing.

    For each claim the report wants to make, this object declares:
      - what fact(s) support it
      - what evidence maturity is required for each expression style
      - what exact wording is safe to use
      - what wording is explicitly forbidden

    Example:
        claim = "境外接收方具备数据安全保障能力"
        fact_status = "user_claim_only"
        allowed_expression = "用户已说明境外接收方具备一定安全保障能力"
        forbidden = ["境外接收方已充分具备安全保障能力", "已通过安全审计确认"]
    """

    strategy_id: str = Field(min_length=1, description="Unique strategy identifier")
    claim: str = Field(
        min_length=1,
        description="The substantive claim the report wants to express",
    )
    fact_refs: list[str] = Field(
        default_factory=list,
        description="FactItem.fact_id values that underpin this claim",
    )

    # ── Evidence gatings ──
    minimum_evidence_status: EvidenceStatus = Field(
        default="documented_evidence",
        description=(
            "The evidence status a fact must have before this claim can be expressed "
            "affirmatively.  user_claim_only facts must use cautious or deferred style."
        ),
    )

    # ── Approved wording ──
    expression_style: ExpressionStyle = Field(
        default="cautious",
        description="Default expression style given current evidence maturity",
    )
    allowed_expression: str = Field(
        min_length=1,
        description="Safe wording approved for external report use",
    )
    recommended_wording: str = Field(
        default="",
        description="The preferred phrasing — what the report generator should use first",
    )

    # ── Forbidden wording ──
    forbidden_expressions: list[str] = Field(
        default_factory=list,
        description="Phrases that MUST NOT appear in any external report for this claim",
    )
    why_forbidden: str = Field(
        default="",
        description="Explanation of why the forbidden expressions are disallowed",
    )

    # ── Metadata ──
    applies_to_jurisdictions: list[str] = Field(
        default_factory=lambda: ["CN"],
        description="Which legal jurisdictions this strategy applies to",
    )


# ── Global forbidden expression rules ─────────────────────────────────────

class ForbiddenExpressionRule(BaseModel):
    """A platform-wide rule that blocks specific language across all modules.

    These are NOT claim-specific — they apply globally to every external report
    regardless of module or jurisdiction.  The QA alignment agent checks every
    generated sentence against this catalogue.
    """

    rule_id: str = Field(min_length=1)
    category: Literal[
        "illegality_claim",        # "违法", "违规" — asserting legal violation
        "over_commitment",         # "完全合规", "已充分证明" — over-promising
        "fact_extrapolation",      # "企业已建立完善的…" — when evidence is thin
        "system_overreach",        # "企业应立刻停止…" — system issuing directives
        "status_misrepresentation",# "已完成" vs "计划实施" — misstating plan as done
    ] = "over_commitment"

    forbidden_pattern: str = Field(
        min_length=1,
        description="Exact phrase or regex pattern that is forbidden",
    )
    replacement_guidance: str = Field(
        min_length=1,
        description="How to rephrase (e.g. '改为：与……存在不一致')",
    )
    severity: Literal["BLOCKER", "HIGH", "MEDIUM"] = "BLOCKER"
    rationale: str = Field(
        default="",
        description="Legal / compliance reason for forbidding this expression",
    )


# ── Pre-built catalogue for CN jurisdiction ───────────────────────────────

def cn_forbidden_expressions() -> list[ForbiddenExpressionRule]:
    """Return the standard catalogue of forbidden expressions for CN compliance reports.

    This is the baseline set — individual modules may add more specific rules.
    """
    return [
        # ── Illegality claims ──
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-001",
            category="illegality_claim",
            forbidden_pattern="违反",
            replacement_guidance="改为：与……存在不一致",
            severity="BLOCKER",
            rationale="系统不能作出违法定性；这是法律意见不是合规辅助",
        ),
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-002",
            category="illegality_claim",
            forbidden_pattern="违法",
            replacement_guidance="改为：可能不符合……相关要求",
            severity="BLOCKER",
            rationale="同上",
        ),
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-003",
            category="illegality_claim",
            forbidden_pattern="违规",
            replacement_guidance="改为：需要进一步满足……规定",
            severity="BLOCKER",
        ),
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-004",
            category="illegality_claim",
            forbidden_pattern="已经构成",
            replacement_guidance="改为：可能存在……风险",
            severity="BLOCKER",
        ),
        # ── Over-commitment ──
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-005",
            category="over_commitment",
            forbidden_pattern="完全合规",
            replacement_guidance="改为：在现有材料条件下，基本满足……要求",
            severity="BLOCKER",
            rationale="即使所有已知检查项都通过，材料缺失和未检查项仍可能存在",
        ),
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-006",
            category="over_commitment",
            forbidden_pattern="已充分证明",
            replacement_guidance="改为：用户已提供……材料",
            severity="BLOCKER",
        ),
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-007",
            category="over_commitment",
            forbidden_pattern="确保不会",
            replacement_guidance="改为：有助于降低……风险",
            severity="HIGH",
        ),
        # ── Fact extrapolation ──
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-008",
            category="fact_extrapolation",
            forbidden_pattern="不存在任何风险",
            replacement_guidance="改为：在当前材料范围内，未发现额外风险点",
            severity="BLOCKER",
            rationale="永远不能说没有任何风险",
        ),
        # ── System overreach ──
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-009",
            category="system_overreach",
            forbidden_pattern="应立刻停止",
            replacement_guidance="改为：建议审慎评估是否继续该处理行为",
            severity="BLOCKER",
            rationale="系统不能给企业发指令",
        ),
        # ── Status misrepresentation ──
        ForbiddenExpressionRule(
            rule_id="CN-FORBIDDEN-010",
            category="status_misrepresentation",
            forbidden_pattern="已完成全部",
            replacement_guidance="改为：已完成……方面的合规工作",
            severity="HIGH",
        ),
    ]
