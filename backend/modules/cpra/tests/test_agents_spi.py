from backend.modules.cpra.agents.spi_sharing_risk_agent import CPRASPISharingRiskAgent
from backend.modules.cpra.schema import CPRAConsentUI, CPRADataItem, CPRADSRMechanism, CPRAVendorInfo


def test_spi_sharing_agent_builds_high_risk_chain_for_spi_third_party_advertising() -> None:
    agent = CPRASPISharingRiskAgent(llm_client=None)

    result = agent.run(
        data_items=[
            CPRADataItem(
                category="health_data",
                is_sensitive=True,
                purpose="insurance_recommendation",
                recipient_type="third_party",
                sale_or_share=True,
            ),
            CPRADataItem(
                category="precise_geolocation",
                is_sensitive=True,
                recipient_type="advertising_network",
                sale_or_share=True,
                cross_context_advertising=True,
            ),
        ],
        vendors=[
            CPRAVendorInfo(name="QuickInsure", vendor_type="third_party", receives_spi=True, sale_or_share=True),
        ],
        dsr_mechanism=CPRADSRMechanism(
            has_web_form=True,
            has_email=True,
            supports_opt_out=False,
            supports_limit_spi=False,
        ),
        consent_ui=CPRAConsentUI(bundled_consent=True),
        notice_facts={},
        data_map_facts={},
        vendor_facts={},
    )

    assert result.risk_chains
    assert any(chain.risk_level == "HIGH" for chain in result.risk_chains)
    assert any(gap.domain == "spi_review" for gap in result.gap_candidates)


def test_spi_sharing_agent_returns_empty_when_no_sensitive_risk_pattern() -> None:
    agent = CPRASPISharingRiskAgent(llm_client=None)

    result = agent.run(
        data_items=[
            CPRADataItem(
                category="usage_analytics",
                is_sensitive=False,
                purpose="analytics",
                recipient_type="internal",
            )
        ],
        vendors=[],
        dsr_mechanism=CPRADSRMechanism(has_web_form=True, has_email=True, supports_opt_out=True, supports_limit_spi=True),
        consent_ui=None,
        notice_facts={},
        data_map_facts={},
        vendor_facts={},
    )

    assert result.risk_chains == []
    assert result.gap_candidates == []
