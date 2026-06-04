"""Vendor contract review agent for CPRA."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.modules.cpra.agents import CPRAAgentBase
from backend.modules.cpra.schema import CPRADataItem, CPRAGapItem, CPRAVendorInfo


class CPRAVendorContractReview(BaseModel):
    vendor_patches: list[CPRAVendorInfo] = Field(default_factory=list)
    contract_gaps: list[CPRAGapItem] = Field(default_factory=list)


class CPRAVendorContractAgent(CPRAAgentBase):
    agent_name = "cpra_vendor_contract"

    def run(
        self,
        *,
        vendor_list_facts: dict,
        contract_texts: list[str],
        vendors: list[CPRAVendorInfo],
        data_items: list[CPRADataItem],
        opt_out_context: str,
    ) -> CPRAVendorContractReview:
        if self.enabled:
            llm_result = self._call_llm("Review vendor contract obligations under CPRA.")
            if llm_result:
                # First slice stays deterministic and only uses fallback review.
                pass
        return self._fallback_review(
            vendor_list_facts=vendor_list_facts,
            contract_texts=contract_texts,
            vendors=vendors,
            data_items=data_items,
            opt_out_context=opt_out_context,
        )

    def _fallback_review(
        self,
        *,
        vendor_list_facts: dict,
        contract_texts: list[str],
        vendors: list[CPRAVendorInfo],
        data_items: list[CPRADataItem],
        opt_out_context: str,
    ) -> CPRAVendorContractReview:
        review = CPRAVendorContractReview()
        combined_contract_text = " ".join(contract_texts).lower()
        has_advertising_flow = any(
            item.recipient_type in {"advertising_network", "third_party"} and item.sale_or_share
            for item in data_items
        )

        for vendor in vendors:
            missing_obligations: list[str] = []
            if vendor.has_dpa and not vendor.dpa_honors_opt_out and (
                vendor.vendor_type in {"ad_partner", "advertising_network", "third_party"} or has_advertising_flow
            ):
                missing_obligations.append("opt-out / GPC")
            if vendor.receives_pi and not vendor.dpa_requires_audit:
                missing_obligations.append("audit rights")
            if vendor.receives_pi and "delete" not in combined_contract_text and "return" not in combined_contract_text:
                missing_obligations.append("deletion / return")
            if vendor.receives_pi and not vendor.dpa_requires_dsr_assist and vendor.vendor_type == "service_provider":
                missing_obligations.append("DSR assistance")

            if missing_obligations:
                review.contract_gaps.append(
                    CPRAGapItem(
                        domain="vendor_review",
                        risk_level="HIGH" if "opt-out / GPC" in missing_obligations else "MEDIUM",
                        gap=(
                            f"供应商'{vendor.name}'合同义务不完整，缺少 "
                            f"{', '.join(missing_obligations)} 条款。"
                        ),
                        legal_basis="CPRA §1798.120, §1798.140(ag), CPPA Regulations",
                        recommendation=(
                            f"修订{vendor.name}相关合同，补齐 "
                            f"{', '.join(missing_obligations)} 义务，并明确用途限制与承接机制。"
                        ),
                        phase="short_term",
                        evidence_source="attachment_extracted",
                    )
                )

        if not vendors and vendor_list_facts.get("has_dpa_mentions") and "opt-out" in opt_out_context.lower():
            review.contract_gaps.append(
                CPRAGapItem(
                    domain="vendor_review",
                    risk_level="MEDIUM",
                    gap="已识别供应商/DPA线索，但缺少可核对的结构化供应商义务信息。",
                    legal_basis="CPRA §1798.140(ag), CPPA Regulations",
                    recommendation="补充供应商清单和合同义务矩阵，特别是 opt-out / audit / deletion 条款。",
                    phase="short_term",
                    evidence_source="attachment_extracted",
                )
            )

        return review
