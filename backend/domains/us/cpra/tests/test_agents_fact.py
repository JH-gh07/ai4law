from backend.domains.us.cpra.agents.fact_extraction_agent import CPRAFactExtractionAgent
from backend.domains.us.cpra.schema import CPRAAttachment


def test_fact_extraction_agent_fallback_builds_structured_facts() -> None:
    agent = CPRAFactExtractionAgent(llm_client=None)

    result = agent.run(
        attachment=CPRAAttachment(
            file_role="data_map",
            file_name="map.csv",
            file_format="csv",
            storage_uri="storage/uploads/map.csv",
        ),
        raw_facts={
            "role": "data_map",
            "categories": ["health_data", "financial_account"],
            "spi_categories": ["health_data", "financial_account"],
            "has_purposes": True,
            "has_recipients": True,
            "has_retention": True,
        },
        business_model="health app",
        data_lifecycle="collect-process-share",
    )

    assert result.extracted_data_items
    assert {item.category for item in result.extracted_data_items} >= {"health_data", "financial_account"}
    assert all(item.is_sensitive for item in result.extracted_data_items)
    assert result.extraction_warnings


def test_fact_extraction_agent_builds_dsr_mechanism_from_rights_sop() -> None:
    agent = CPRAFactExtractionAgent(llm_client=None)

    result = agent.run(
        attachment=CPRAAttachment(
            file_role="rights_sop",
            file_name="rights.docx",
            file_format="docx",
            storage_uri="storage/uploads/rights.docx",
        ),
        raw_facts={
            "role": "rights_sop",
            "response_days": 30,
            "supports_access": True,
            "supports_delete": True,
            "supports_correct": True,
            "supports_opt_out": False,
            "has_verification_process": True,
            "has_extension_procedure": True,
        },
        business_model="saas",
        data_lifecycle="collect-store",
    )

    assert result.extracted_dsr_mechanism is not None
    assert result.extracted_dsr_mechanism.response_days == 30
    assert result.extracted_dsr_mechanism.supports_access is True
    assert result.extracted_dsr_mechanism.supports_opt_out is False
