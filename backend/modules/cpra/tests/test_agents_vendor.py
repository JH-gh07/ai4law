from backend.modules.cpra.agents.vendor_contract_agent import CPRAVendorContractAgent
from backend.modules.cpra.schema import CPRADataItem, CPRAVendorInfo


def test_vendor_contract_agent_flags_missing_opt_out_and_audit_obligations() -> None:
    agent = CPRAVendorContractAgent(llm_client=None)

    result = agent.run(
        vendor_list_facts={
            "role": "vendor_list",
            "vendors": ["AdNetwork Alpha"],
            "has_dpa_mentions": True,
            "has_service_provider": False,
            "has_contractor": False,
        },
        contract_texts=[
            "AdNetwork Alpha may use personal data for personalized advertising. "
            "DPA exists but does not mention opt-out, audit rights, or deletion return obligations."
        ],
        vendors=[
            CPRAVendorInfo(
                name="AdNetwork Alpha",
                vendor_type="ad_partner",
                receives_pi=True,
                receives_spi=False,
                sale_or_share=True,
                has_dpa=True,
                dpa_honors_opt_out=False,
                dpa_requires_audit=False,
            )
        ],
        data_items=[
            CPRADataItem(
                category="browsing_behavior",
                recipient_type="advertising_network",
                sale_or_share=True,
            )
        ],
        opt_out_context="存在广告共享，但未承接消费者 opt-out / GPC 指令。",
    )

    assert result.contract_gaps
    assert any(gap.domain == "vendor_review" for gap in result.contract_gaps)
    assert any("opt-out" in gap.gap.lower() or "选择退出" in gap.gap for gap in result.contract_gaps)


def test_vendor_contract_agent_returns_empty_when_contract_obligations_are_complete() -> None:
    agent = CPRAVendorContractAgent(llm_client=None)

    result = agent.run(
        vendor_list_facts={},
        contract_texts=[
            "Service provider DPA prohibits sale/share, requires DSR assistance, "
            "audit rights, deletion or return, and honors opt-out requests."
        ],
        vendors=[
            CPRAVendorInfo(
                name="Processor One",
                vendor_type="service_provider",
                receives_pi=True,
                sale_or_share=False,
                has_dpa=True,
                dpa_prohibits_sale_share=True,
                dpa_requires_dsr_assist=True,
                dpa_requires_audit=True,
                dpa_honors_opt_out=True,
            )
        ],
        data_items=[],
        opt_out_context="",
    )

    assert result.contract_gaps == []
