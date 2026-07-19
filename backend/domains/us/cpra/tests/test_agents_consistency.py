from backend.domains.us.cpra.agents.consistency_review_agent import CPRAConsistencyReviewAgent
from backend.domains.us.cpra.schema import CPRAChapter, CPRAGapItem


def test_consistency_agent_flags_softened_high_risk_spi_and_vendor_omission() -> None:
    agent = CPRAConsistencyReviewAgent(llm_client=None)

    result = agent.run(
        payload_summary={
            "company_name": "Health app",
            "has_spi": True,
        },
        gap_items=[
            CPRAGapItem(
                domain="spi_review",
                risk_level="HIGH",
                gap="健康数据存在高风险共享组合。",
                legal_basis="CPRA §1798.121",
                recommendation="停止高风险共享。",
                phase="short_term",
            ),
            CPRAGapItem(
                domain="vendor_review",
                risk_level="HIGH",
                gap="广告合作伙伴合同缺少 opt-out / audit 条款。",
                legal_basis="CPRA §1798.120",
                recommendation="修订合同。",
                phase="short_term",
            ),
        ],
        chapters=[
            CPRAChapter(
                chapter_no=1,
                title="执行摘要",
                content="总体风险可控，现有措施基本充分。",
                citations=[],
                risk_level="LOW",
            ),
            CPRAChapter(
                chapter_no=5,
                title="敏感信息与第三方管理",
                content="本文主要讨论一般性数据实践。",
                citations=[],
                risk_level="LOW",
            ),
            CPRAChapter(
                chapter_no=6,
                title="行动清单与优先级",
                content="下一步继续常规治理。",
                citations=[],
                risk_level="LOW",
            ),
        ],
    )

    assert result.issues
    assert any("高风险" in issue.issue or "HIGH" in issue.issue for issue in result.issues)
    assert any("SPI" in issue.issue or "敏感" in issue.issue for issue in result.issues)
    assert any("vendor" in issue.issue.lower() or "供应商" in issue.issue for issue in result.issues)


def test_consistency_agent_returns_clean_when_chapters_cover_major_risks() -> None:
    agent = CPRAConsistencyReviewAgent(llm_client=None)

    result = agent.run(
        payload_summary={"company_name": "SaaS"},
        gap_items=[
            CPRAGapItem(
                domain="spi_review",
                risk_level="HIGH",
                gap="存在 SPI 风险。",
                legal_basis="CPRA §1798.121",
                recommendation="补充 Limit SPI。",
                phase="short_term",
            ),
            CPRAGapItem(
                domain="vendor_review",
                risk_level="MEDIUM",
                gap="供应商合同需补充审计权。",
                legal_basis="CPRA §1798.140(ag)",
                recommendation="补合同。",
                phase="short_term",
            ),
        ],
        chapters=[
            CPRAChapter(
                chapter_no=1,
                title="执行摘要",
                content="存在高风险事项，需立即整改敏感信息和供应商合同控制。",
                citations=[],
                risk_level="HIGH",
            ),
            CPRAChapter(
                chapter_no=5,
                title="敏感信息与第三方管理",
                content="SPI 使用、Limit SPI 和第三方共享义务均需重点整改。",
                citations=[],
                risk_level="HIGH",
            ),
            CPRAChapter(
                chapter_no=6,
                title="行动清单与优先级",
                content="行动清单包括修订供应商合同、加入 audit / opt-out 条款。",
                citations=[],
                risk_level="HIGH",
            ),
        ],
    )

    assert result.issues == []
