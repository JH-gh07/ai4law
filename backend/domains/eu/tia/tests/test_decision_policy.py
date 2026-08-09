from backend.domains.eu.tia.decision_policy import evaluate_tia_decision
from backend.domains.eu.tia.agents.dpo_review_agent import DPOReviewAgent
from backend.domains.eu.tia.attachment_evidence import TIAAttachmentEvidence
from backend.domains.eu.tia.schema import TIAAttachment
from backend.domains.eu.tia.schema import TIAStructuredInput


def _high_risk_input() -> TIAStructuredInput:
    return TIAStructuredInput(
        exporter_country="DE",
        importer_country="US",
        destination_country="US",
        exporter_role="controller",
        importer_role="processor",
        encryption_before_transfer=True,
        key_managed_in_eu=True,
        has_end_to_end_encryption=True,
        has_key_separation=True,
    )


def test_high_risk_claims_without_control_evidence_require_suspension() -> None:
    decision = evaluate_tia_decision(
        transfer_tool="scc",
        structured_input=_high_risk_input(),
        inherent_risk="HIGH",
        residual_risk="MEDIUM",
        measure_sufficiency="sufficient",
        attachment_evidences=[{
            "role": "country_law_analysis",
            "has_gov_access_analysis": True,
        }],
        consistency_issues=[],
    )

    assert decision.transfer_status == "suspend"
    assert decision.evidence_status == "missing"
    assert "签署或适用的传输工具文件" in decision.missing_evidence
    assert "技术控制实施证据" in decision.missing_evidence


def test_verified_scc_and_strong_controls_allow_only_conditional_proceeding() -> None:
    decision = evaluate_tia_decision(
        transfer_tool="scc",
        structured_input=_high_risk_input(),
        inherent_risk="HIGH",
        residual_risk="MEDIUM",
        measure_sufficiency="sufficient",
        attachment_evidences=[
            {
                "role": "transfer_agreement",
                "has_scc_mention": True,
                "is_2021_914_scc": True,
                "has_module_selection": True,
            },
            {
                "role": "country_law_analysis",
                "has_gov_access_analysis": True,
                "has_remedy_assessment": True,
                "has_oversight_assessment": True,
            },
            {
                "role": "technical_control_doc",
                "has_end_to_end_encryption": True,
                "has_key_management": True,
                "key_location_eu": True,
                "has_key_separation": True,
            },
        ],
        consistency_issues=[],
    )

    assert decision.transfer_status == "proceed_with_conditions"
    assert decision.evidence_status == "verified"
    assert decision.missing_evidence == []


def test_high_residual_risk_requires_suspension_even_with_evidence() -> None:
    decision = evaluate_tia_decision(
        transfer_tool="scc",
        structured_input=_high_risk_input(),
        inherent_risk="HIGH",
        residual_risk="HIGH",
        measure_sufficiency="insufficient",
        attachment_evidences=[
            {"role": "transfer_agreement", "has_scc_mention": True},
            {"role": "technical_control_doc", "has_end_to_end_encryption": True},
        ],
        consistency_issues=[],
    )

    assert decision.transfer_status == "suspend"
    assert any("剩余风险仍为 HIGH" in reason for reason in decision.reasons)
    assert decision.decision_source == "deterministic_rule"


def test_policy_checks_all_attachments_instead_of_only_the_first() -> None:
    decision = evaluate_tia_decision(
        transfer_tool="scc",
        structured_input=_high_risk_input(),
        inherent_risk="HIGH",
        residual_risk="MEDIUM",
        measure_sufficiency="sufficient",
        attachment_evidences=[
            {"role": "transfer_agreement", "has_scc_mention": False},
            {
                "role": "transfer_agreement",
                "has_scc_mention": True,
                "is_2021_914_scc": True,
                "has_module_selection": True,
            },
            {"role": "country_law_analysis", "has_gov_access_analysis": True},
            {"role": "country_law_analysis", "has_remedy_assessment": True},
            {"role": "country_law_analysis", "has_oversight_assessment": True},
            {"role": "technical_control_doc", "has_end_to_end_encryption": False},
            {
                "role": "technical_control_doc",
                "has_end_to_end_encryption": True,
                "has_key_management": True,
                "key_location_eu": True,
            },
        ],
        consistency_issues=[],
    )

    assert decision.transfer_status == "proceed_with_conditions"
    assert decision.evidence_status == "verified"


def test_bcr_is_not_verified_by_an_unrelated_agreement() -> None:
    decision = evaluate_tia_decision(
        transfer_tool="bcr",
        structured_input=_high_risk_input(),
        inherent_risk="HIGH",
        residual_risk="MEDIUM",
        measure_sufficiency="sufficient",
        attachment_evidences=[
            {"role": "transfer_agreement", "has_bcr_mention": False},
            {
                "role": "country_law_analysis",
                "has_gov_access_analysis": True,
                "has_remedy_assessment": True,
                "has_oversight_assessment": True,
            },
            {
                "role": "technical_control_doc",
                "has_end_to_end_encryption": True,
                "has_key_management": True,
                "key_location_eu": True,
            },
        ],
        consistency_issues=[],
    )

    assert decision.transfer_status == "suspend"
    assert "签署或适用的传输工具文件" in decision.missing_evidence


def test_attachment_extractor_reuses_preparsed_text() -> None:
    class _ParserMustNotRun:
        def parse_text(self, storage_uri: str) -> str:
            raise AssertionError(f"unexpected second parse: {storage_uri}")

    attachment = TIAAttachment(
        file_role="technical_control_doc",
        file_name="controls.pdf",
        file_format="pdf",
        storage_uri="controls.pdf",
    )

    evidence = TIAAttachmentEvidence(parser=_ParserMustNotRun()).extract(
        attachment,
        text="End-to-end encryption with EU key management and key separation.",
    )

    assert evidence["has_end_to_end_encryption"] is True
    assert evidence["has_key_management"] is True
    assert evidence["key_location_eu"] is True
    assert evidence["has_key_separation"] is True


def test_dpo_fallback_uses_residual_risk_semantics() -> None:
    result = DPOReviewAgent(None).run(
        route="full_tia_scc",
        country_risk_level="HIGH",
        sensitivity="medium",
        measure_overall="insufficient",
        residual_risk="HIGH",
        issues=["Effective measures are not evidenced."],
        chapter_summaries=[],
    )

    assert result["review_result"] == "needs_revision"
