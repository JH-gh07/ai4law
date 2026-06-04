"""Fact extraction agent for CPRA attachment materials."""

from __future__ import annotations

from backend.modules.cpra.agents import CPRAAgentBase
from backend.modules.cpra.schema import (
    CPRAAttachment,
    CPRAConsentUI,
    CPRADataItem,
    CPRADSRMechanism,
    CPRAEvidenceSpan,
    CPRAFactPack,
    CPRAVendorInfo,
)

_SENSITIVE_CATEGORY_MAP = {
    "health_data": ("health_data", True),
    "biometric_information": ("biometric_information", True),
    "precise_geolocation": ("precise_geolocation", True),
    "financial_account": ("financial_account", True),
    "account_credentials": ("account_credentials", True),
    "racial_or_ethnic_origin": ("racial_or_ethnic_origin", True),
    "personal_identifier": ("personal_identifier", False),
}


class CPRAFactExtractionAgent(CPRAAgentBase):
    agent_name = "cpra_fact_extraction"

    def run(
        self,
        *,
        attachment: CPRAAttachment,
        raw_facts: dict,
        business_model: str,
        data_lifecycle: str,
    ) -> CPRAFactPack:
        if self.enabled:
            llm_result = self._call_llm(
                self._build_prompt(
                    attachment=attachment,
                    raw_facts=raw_facts,
                    business_model=business_model,
                    data_lifecycle=data_lifecycle,
                )
            )
            if llm_result:
                # First slice keeps LLM use conservative and falls back to deterministic shaping.
                # We only rely on fallback shaping until targeted tests and contracts expand.
                pass
        return self._fallback_fact_pack(attachment=attachment, raw_facts=raw_facts)

    @staticmethod
    def _build_prompt(
        *,
        attachment: CPRAAttachment,
        raw_facts: dict,
        business_model: str,
        data_lifecycle: str,
    ) -> str:
        return (
            "Extract structured CPRA facts from the attachment summary.\n"
            f"file_role={attachment.file_role}\n"
            f"file_name={attachment.file_name}\n"
            f"business_model={business_model}\n"
            f"data_lifecycle={data_lifecycle}\n"
            f"raw_facts={raw_facts}\n"
            "Return JSON with extracted_data_items, extracted_dsr_mechanism, "
            "extracted_vendors, extracted_consent_ui, evidence_spans, extraction_warnings."
        )

    def _fallback_fact_pack(self, *, attachment: CPRAAttachment, raw_facts: dict) -> CPRAFactPack:
        fact_pack = CPRAFactPack(source_file=attachment)
        role = raw_facts.get("role")

        if role == "data_map":
            categories = raw_facts.get("categories", []) or []
            fact_pack.extracted_data_items = [
                self._build_data_item(category) for category in categories
            ]
            if categories:
                fact_pack.evidence_spans = [
                    CPRAEvidenceSpan(
                        fact_id=f"data_item.{category}",
                        source_file=attachment.file_name,
                        quote=category,
                        confidence=0.6,
                    )
                    for category in categories
                ]
                fact_pack.extraction_warnings.append(
                    "Data items were inferred from attachment keywords and should be reviewed."
                )

        elif role == "rights_sop":
            fact_pack.extracted_dsr_mechanism = CPRADSRMechanism(
                has_web_form=bool(raw_facts.get("supports_access") or raw_facts.get("supports_delete")),
                has_email=bool(raw_facts.get("has_verification_process") or raw_facts.get("supports_access")),
                supports_access=bool(raw_facts.get("supports_access")),
                supports_delete=bool(raw_facts.get("supports_delete")),
                supports_correct=bool(raw_facts.get("supports_correct")),
                supports_opt_out=bool(raw_facts.get("supports_opt_out")),
                response_days=raw_facts.get("response_days"),
                is_easy_to_find=bool(raw_facts.get("has_verification_process")),
            )
            fact_pack.extraction_warnings.append(
                "DSR mechanism was inferred from SOP indicators and may need manual confirmation."
            )

        elif role == "vendor_list":
            vendor_names = raw_facts.get("vendors", []) or []
            fact_pack.extracted_vendors = [
                CPRAVendorInfo(
                    name=name.strip(),
                    has_dpa=bool(raw_facts.get("has_dpa_mentions")),
                    dpa_honors_opt_out=bool(raw_facts.get("has_service_provider")),
                )
                for name in vendor_names
                if name.strip()
            ]
            if fact_pack.extracted_vendors:
                fact_pack.extraction_warnings.append(
                    "Vendor obligations were inferred from vendor list keywords and require contract review."
                )

        elif role == "privacy_policy":
            fact_pack.extracted_consent_ui = CPRAConsentUI(
                has_cookie_banner=bool(raw_facts.get("has_opt_out_link")),
                confusing_language=not bool(raw_facts.get("has_category_disclosure")),
            )
            fact_pack.extraction_warnings.append(
                "Privacy policy facts were normalized from keyword extraction only."
            )

        return fact_pack

    @staticmethod
    def _build_data_item(category: str) -> CPRADataItem:
        normalized, is_sensitive = _SENSITIVE_CATEGORY_MAP.get(category, (category, False))
        return CPRADataItem(
            category=normalized,
            is_sensitive=is_sensitive,
            spi_type=normalized if is_sensitive else None,
        )
