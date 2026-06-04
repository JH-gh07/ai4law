"""SPI / sharing risk review agent for CPRA."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.modules.cpra.agents import CPRAAgentBase
from backend.modules.cpra.schema import CPRAConsentUI, CPRADataItem, CPRADSRMechanism, CPRAGapItem, CPRARiskChain, CPRAVendorInfo

_HIGH_RISK_PURPOSES = {
    "advertising",
    "marketing",
    "third_party_marketing",
    "insurance_recommendation",
    "data_broker",
    "sale",
}


class CPRASPIRiskReview(BaseModel):
    risk_chains: list[CPRARiskChain] = Field(default_factory=list)
    gap_candidates: list[CPRAGapItem] = Field(default_factory=list)
    data_item_patches: list[CPRADataItem] = Field(default_factory=list)
    vendor_patches: list[CPRAVendorInfo] = Field(default_factory=list)


class CPRASPISharingRiskAgent(CPRAAgentBase):
    agent_name = "cpra_spi_sharing_risk"

    def run(
        self,
        *,
        data_items: list[CPRADataItem],
        vendors: list[CPRAVendorInfo],
        dsr_mechanism: CPRADSRMechanism | None,
        consent_ui: CPRAConsentUI | None,
        notice_facts: dict,
        data_map_facts: dict,
        vendor_facts: dict,
    ) -> CPRASPIRiskReview:
        if self.enabled:
            llm_result = self._call_llm(
                "Review SPI sharing risk combinations for CPRA from structured facts only."
            )
            if llm_result:
                # First slice remains deterministic even when LLM is available.
                pass
        return self._fallback_review(
            data_items=data_items,
            vendors=vendors,
            dsr_mechanism=dsr_mechanism,
            consent_ui=consent_ui,
        )

    def _fallback_review(
        self,
        *,
        data_items: list[CPRADataItem],
        vendors: list[CPRAVendorInfo],
        dsr_mechanism: CPRADSRMechanism | None,
        consent_ui: CPRAConsentUI | None,
    ) -> CPRASPIRiskReview:
        review = CPRASPIRiskReview()
        if not any(item.is_sensitive for item in data_items):
            return review

        for item in data_items:
            if not item.is_sensitive:
                continue

            risky_purpose = item.purpose in _HIGH_RISK_PURPOSES
            risky_recipient = item.recipient_type in {"third_party", "advertising_network"}
            risky_share = item.sale_or_share or item.cross_context_advertising
            missing_opt_out = dsr_mechanism is not None and not dsr_mechanism.supports_opt_out
            missing_limit_spi = dsr_mechanism is not None and not dsr_mechanism.supports_limit_spi
            dark_pattern = consent_ui is not None and (consent_ui.bundled_consent or consent_ui.preselected_consent)

            if risky_purpose or (risky_recipient and risky_share):
                facts = [f"spi={item.category}"]
                if item.purpose:
                    facts.append(f"purpose={item.purpose}")
                if item.recipient_type:
                    facts.append(f"recipient={item.recipient_type}")
                if item.sale_or_share:
                    facts.append("sale_or_share=true")
                if item.cross_context_advertising:
                    facts.append("cross_context_advertising=true")
                if missing_opt_out:
                    facts.append("opt_out_missing=true")
                if missing_limit_spi:
                    facts.append("limit_spi_missing=true")
                if dark_pattern:
                    facts.append("dark_pattern=true")

                review.risk_chains.append(
                    CPRARiskChain(
                        chain_id=f"spi_chain_{item.category}",
                        facts=facts,
                        risk_level="HIGH",
                        gap=(
                            f"敏感个人信息'{item.category}'存在高风险组合使用/共享，"
                            "需要复核其用途、接收方及退出机制。"
                        ),
                        recommendation=(
                            "优先停止或限制该SPI处理路径，并补充 Do Not Sell or Share / "
                            "Limit Use of Sensitive Personal Information 机制。"
                        ),
                    )
                )
                review.gap_candidates.append(
                    CPRAGapItem(
                        domain="spi_review",
                        risk_level="HIGH",
                        gap=(
                            f"敏感个人信息'{item.category}'涉及高风险用途或第三方共享，"
                            "且退出/限制机制可能不足。"
                        ),
                        legal_basis="CPRA §1798.120, §1798.121",
                        recommendation="复核 SPI 使用必要性、共享路径和消费者控制入口。",
                        phase="short_term",
                        evidence_source="rule_inferred",
                    )
                )

        if not review.risk_chains and any(v.receives_spi and v.sale_or_share for v in vendors):
            review.gap_candidates.append(
                CPRAGapItem(
                    domain="spi_review",
                    risk_level="HIGH",
                    gap="供应商侧存在 SPI 共享风险，需要核对共享场景与控制措施。",
                    legal_basis="CPRA §1798.120, §1798.121",
                    recommendation="核查接收 SPI 的第三方/供应商是否具备限制使用和退出承接义务。",
                    phase="short_term",
                    evidence_source="rule_inferred",
                )
            )
        return review
