from backend.common.citation.module_grounding import (
    ModuleIssue,
    build_module_citation_bundle,
)


def test_module_grounding_preserves_registered_paragraph_locator() -> None:
    issue = ModuleIssue(
        issue_id="ISSUE-1",
        category="cross_border",
        title="第三国传输影响评估",
        description="核对 Article 46 传输工具是否有效。",
        severity="HIGH",
    )
    bundle = build_module_citation_bundle(
        module="eu_scc",
        jurisdiction="EU",
        issues=[issue],
        regulations_by_issue={
            issue.issue_id: [
                {
                    "source_id": "EU-GUIDE-002",
                    "source_title": "EDPB Recommendations 01/2020",
                    "title": "EDPB Recommendations 01/2020",
                    "article": "Step 3",
                    "content": "Step 3 assesses whether the Article 46 transfer tool is effective.",
                    "source_kind": "official_guide",
                    "authority_level": "medium",
                    "binding_force": "recommended",
                }
            ]
        },
    )

    assert bundle.items[0].article_no == "Step 3"


def test_tia_grounding_rejects_wrong_gdpr_locator() -> None:
    issue = ModuleIssue(
        issue_id="ISSUE-TRANSFER-TOOL",
        category="transfer_tool",
        title="SCC 传输工具",
        description="核对 GDPR Article 46 适当保障是否成立。",
        severity="HIGH",
    )
    bundle = build_module_citation_bundle(
        module="tia",
        jurisdiction="EU",
        issues=[issue],
        regulations_by_issue={
            issue.issue_id: [
                {
                    "source_id": "EU-LAW-001",
                    "source_title": "GDPR (EU) 2016/679",
                    "article": "段落1",
                    "content": "GDPR document title without the cited rule.",
                    "source_kind": "law_article",
                },
                {
                    "source_id": "EU-LAW-001",
                    "source_title": "GDPR (EU) 2016/679",
                    "article": "Article 46",
                    "content": "Appropriate safeguards and effective legal remedies are required.",
                    "source_kind": "law_article",
                },
            ]
        },
    )

    assert [item.article_no for item in bundle.items] == ["46"]
    assert bundle.items[0].citation_id == "CIT-EU-GDPR-ART46-P01"
