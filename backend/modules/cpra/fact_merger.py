"""Merge structured facts inferred from CPRA attachments into the request payload."""

from __future__ import annotations

from backend.modules.cpra.schema import CPRAFactPack, CPRARequest


class CPRAFactMerger:
    """Merge inferred facts conservatively.

    Explicit user input always wins over agent-inferred or extractor-derived facts.
    """

    def merge(self, payload: CPRARequest, fact_packs: list[CPRAFactPack]) -> CPRARequest:
        data_items = payload.data_items
        dsr_mechanism = payload.dsr_mechanism
        vendors = payload.vendors
        consent_ui = payload.consent_ui

        if not data_items:
            for pack in fact_packs:
                if pack.extracted_data_items:
                    data_items = pack.extracted_data_items
                    break

        if dsr_mechanism is None:
            for pack in fact_packs:
                if pack.extracted_dsr_mechanism is not None:
                    dsr_mechanism = pack.extracted_dsr_mechanism
                    break

        if not vendors:
            for pack in fact_packs:
                if pack.extracted_vendors:
                    vendors = pack.extracted_vendors
                    break

        if consent_ui is None:
            for pack in fact_packs:
                if pack.extracted_consent_ui is not None:
                    consent_ui = pack.extracted_consent_ui
                    break

        return payload.model_copy(
            update={
                "data_items": data_items,
                "dsr_mechanism": dsr_mechanism,
                "vendors": vendors,
                "consent_ui": consent_ui,
            }
        )
