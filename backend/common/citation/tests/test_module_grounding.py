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
                    "article": "段落6",
                    "content": "Step 3 assesses whether the Article 46 transfer tool is effective.",
                    "source_kind": "official_guide",
                    "authority_level": "medium",
                    "binding_force": "recommended",
                }
            ]
        },
    )

    assert bundle.items[0].article_no == "段落6"
