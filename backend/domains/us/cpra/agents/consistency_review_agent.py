"""Consistency review agent for CPRA report outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.domains.us.cpra.agents import CPRAAgentBase
from backend.domains.us.cpra.schema import CPRAChapter, CPRAConsistencyIssue, CPRAGapItem


class CPRAConsistencyReview(BaseModel):
    issues: list[CPRAConsistencyIssue] = Field(default_factory=list)


class CPRAConsistencyReviewAgent(CPRAAgentBase):
    agent_name = "cpra_consistency_review"

    def run(
        self,
        *,
        payload_summary: dict,
        gap_items: list[CPRAGapItem],
        chapters: list[CPRAChapter],
    ) -> CPRAConsistencyReview:
        if self.enabled:
            llm_result = self._call_llm("Review CPRA report consistency against structured risk findings.")
            if llm_result:
                # First slice stays deterministic.
                pass
        return self._fallback_review(gap_items=gap_items, chapters=chapters)

    def _fallback_review(
        self,
        *,
        gap_items: list[CPRAGapItem],
        chapters: list[CPRAChapter],
    ) -> CPRAConsistencyReview:
        review = CPRAConsistencyReview()
        combined_text = " ".join(ch.content for ch in chapters).lower()
        summary_text = " ".join(ch.content for ch in chapters if ch.chapter_no == 1).lower()
        action_text = " ".join(ch.content for ch in chapters if ch.chapter_no == 6).lower()

        has_high_gap = any(g.risk_level == "HIGH" for g in gap_items)
        if has_high_gap and any(token in summary_text for token in ["可控", "基本充分", "low risk"]):
            review.issues.append(
                CPRAConsistencyIssue(
                    issue="报告执行摘要弱化了 HIGH 风险结论。",
                    severity="HIGH",
                    suggested_fix="执行摘要应明确存在高风险事项及短期整改要求。",
                )
            )

        has_spi_gap = any(g.domain in {"spi", "spi_review"} for g in gap_items)
        if has_spi_gap and not any(token in combined_text for token in ["spi", "敏感", "limit spi"]):
            review.issues.append(
                CPRAConsistencyIssue(
                    issue="报告遗漏了 SPI / Limit SPI 相关高风险事项。",
                    severity="HIGH",
                    suggested_fix="在敏感信息章节明确写入 SPI 风险、限制使用义务和整改措施。",
                )
            )

        has_vendor_gap = any(g.domain in {"vendor_management", "vendor_review"} for g in gap_items)
        if has_vendor_gap and not any(token in action_text for token in ["vendor", "供应商", "合同", "audit", "opt-out"]):
            review.issues.append(
                CPRAConsistencyIssue(
                    issue="行动清单遗漏了供应商/合同义务整改事项。",
                    severity="MEDIUM",
                    suggested_fix="在行动清单中加入供应商合同修订、audit、opt-out/GPC 承接等任务。",
                )
            )

        return review
