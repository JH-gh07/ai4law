from backend.modules.cpra.schema import CPRARequest
from backend.modules.cpra.service import CPRAService
from backend.modules.cpra.schema import CPRAChapter


def _fast_render(task_id, payload, chapters, gaps, attachment_notes, citation_registry):
    return {
        "markdown": "outputs/cpra/test.md",
        "docx": "outputs/cpra/test.docx",
        "pdf": "outputs/cpra/test.pdf",
        "xlsx": "outputs/cpra/test.xlsx",
        "zip": "outputs/cpra/test.zip",
        "citation_map_json": "outputs/cpra/citation_map.json",
    }


def _fast_chapters(*_args, **_kwargs):
    return [
        CPRAChapter(
            chapter_no=1,
            title="执行摘要",
            content="存在高风险事项，需整改。",
            citations=[],
            risk_level="HIGH",
        ),
        CPRAChapter(
            chapter_no=5,
            title="敏感信息与第三方管理",
            content="SPI 使用、共享和 Limit SPI 义务需要整改。",
            citations=[],
            risk_level="HIGH",
        ),
        CPRAChapter(
            chapter_no=6,
            title="行动清单与优先级",
            content="行动清单包括供应商合同、audit、opt-out 和 SPI 整改。",
            citations=[],
            risk_level="HIGH",
        ),
    ]


def test_cpra_generate_report(monkeypatch) -> None:
    monkeypatch.setenv("AI4LAW_CPRA_DISABLE_AGENT_LLM", "1")
    monkeypatch.setenv("AI4LAW_CPRA_FAST_RETRIEVE", "1")
    service = CPRAService()
    service._render = _fast_render
    service._generate_chapters_from_context = _fast_chapters
    payload = CPRARequest.model_validate(
        {
            "company_name": "测试企业",
            "business_model": "SaaS",
            "data_lifecycle": "收集-处理-存储-删除",
            "notice_and_consent": "隐私告知缺失",
            "consumer_rights_process": "目前仅邮箱接收",
            "opt_out_and_sale_sharing": "存在共享但无opt-out",
            "vendor_management": "供应商管理未体现DPA",
            "attachments": [
                {
                    "file_role": "privacy_policy",
                    "file_name": "policy.url",
                    "file_format": "url",
                    "storage_uri": "https://example.com/privacy",
                }
            ],
        }
    )

    result = service.generate_report(payload)
    assert result.report_path.endswith(".docx")
    assert result.report_path == "outputs/cpra/test.docx"
    assert result.output_files["pdf"].endswith(".pdf")
    assert result.output_files["xlsx"].endswith(".xlsx")
    assert result.gap_items


def test_cpra_generate_report_uses_enhanced_attachment_facts(monkeypatch) -> None:
    monkeypatch.setenv("AI4LAW_CPRA_DISABLE_AGENT_LLM", "1")
    monkeypatch.setenv("AI4LAW_CPRA_FAST_RETRIEVE", "1")
    service = CPRAService()
    payload = CPRARequest.model_validate(
        {
            "company_name": "测试企业",
            "business_model": "Health app",
            "data_lifecycle": "收集-处理-共享",
            "notice_and_consent": "notice text",
            "consumer_rights_process": "rights text",
            "opt_out_and_sale_sharing": "share text",
            "vendor_management": "DPA exists but does not mention opt-out, audit, deletion return obligations.",
            "attachments": [
                {
                    "file_role": "data_map",
                    "file_name": "map.csv",
                    "file_format": "csv",
                    "storage_uri": "storage/uploads/map.csv",
                },
                {
                    "file_role": "vendor_list",
                    "file_name": "vendors.csv",
                    "file_format": "csv",
                    "storage_uri": "storage/uploads/vendors.csv",
                }
            ],
        }
    )

    def _extractor_stub(attachment):
        if attachment.file_role == "data_map":
            return {
                "role": "data_map",
                "categories": ["health_data"],
                "spi_categories": ["health_data"],
                "has_purposes": True,
                "has_recipients": True,
                "has_retention": True,
            }
        return {
            "role": "vendor_list",
            "vendors": ["AdNetwork Alpha"],
            "has_dpa_mentions": True,
            "has_service_provider": False,
            "has_contractor": False,
        }

    service.extractor.extract = _extractor_stub
    captured = {}

    def _fake_render(task_id, payload, chapters, gaps, attachment_notes, citation_registry):
        captured["payload"] = payload
        captured["gaps"] = gaps
        return _fast_render(task_id, payload, chapters, gaps, attachment_notes, citation_registry)

    service._render = _fake_render
    service._generate_chapters_from_context = _fast_chapters

    result = service.generate_report(payload)

    assert captured["payload"].data_items
    assert captured["payload"].data_items[0].category == "health_data"
    assert any(g.domain == "spi" for g in captured["gaps"])
    assert any(g.risk_level == "HIGH" for g in captured["gaps"])
    assert any(g.domain == "vendor_review" for g in captured["gaps"])
    assert result.output_files["docx"].endswith(".docx")


def test_cpra_generate_report_adds_consistency_review_issues(monkeypatch) -> None:
    monkeypatch.setenv("AI4LAW_CPRA_DISABLE_AGENT_LLM", "1")
    monkeypatch.setenv("AI4LAW_CPRA_FAST_RETRIEVE", "1")
    service = CPRAService()
    payload = CPRARequest.model_validate(
        {
            "company_name": "测试企业",
            "business_model": "Health app",
            "data_lifecycle": "收集-处理-共享",
            "notice_and_consent": "notice text",
            "consumer_rights_process": "rights text",
            "opt_out_and_sale_sharing": "share text",
            "vendor_management": "DPA exists but does not mention opt-out or audit obligations.",
            "attachments": [
                {
                    "file_role": "data_map",
                    "file_name": "map.csv",
                    "file_format": "csv",
                    "storage_uri": "storage/uploads/map.csv",
                },
                {
                    "file_role": "vendor_list",
                    "file_name": "vendors.csv",
                    "file_format": "csv",
                    "storage_uri": "storage/uploads/vendors.csv",
                }
            ],
        }
    )

    def _extractor_stub(attachment):
        if attachment.file_role == "data_map":
            return {
                "role": "data_map",
                "categories": ["health_data"],
                "spi_categories": ["health_data"],
                "has_purposes": True,
                "has_recipients": True,
                "has_retention": True,
            }
        return {
            "role": "vendor_list",
            "vendors": ["AdNetwork Alpha"],
            "has_dpa_mentions": True,
            "has_service_provider": False,
            "has_contractor": False,
        }

    service.extractor.extract = _extractor_stub
    service._render = _fast_render
    service._generate_chapters_from_context = lambda context_block, level, citations, citation_registry, citation_bundle: [
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
    ]

    result = service.generate_report(payload)

    assert result.consistency_issues
    assert any("高风险" in issue or "HIGH" in issue for issue in result.consistency_issues)
    assert any("SPI" in issue or "敏感" in issue for issue in result.consistency_issues)
    assert any("供应商" in issue or "合同" in issue for issue in result.consistency_issues)


def test_cpra_generate_report_prefers_gap_level_citations(monkeypatch) -> None:
    monkeypatch.setenv("AI4LAW_CPRA_DISABLE_AGENT_LLM", "1")
    service = CPRAService()
    payload = CPRARequest.model_validate(
        {
            "company_name": "测试企业",
            "business_model": "Health app",
            "data_lifecycle": "收集-处理-共享",
            "notice_and_consent": "notice text",
            "consumer_rights_process": "rights text",
            "opt_out_and_sale_sharing": "share text",
            "vendor_management": "DPA exists but does not mention opt-out or audit obligations.",
            "attachments": [
                {
                    "file_role": "data_map",
                    "file_name": "map.csv",
                    "file_format": "csv",
                    "storage_uri": "storage/uploads/map.csv",
                }
            ],
        }
    )

    service.extractor.extract = lambda _attachment: {
        "role": "data_map",
        "categories": ["health_data"],
        "spi_categories": ["health_data"],
        "has_purposes": True,
        "has_recipients": True,
        "has_retention": True,
    }
    service._render = _fast_render
    service._generate_chapters_from_context = lambda context_block, level, citations, citation_registry, citation_bundle: [
        CPRAChapter(chapter_no=1, title="执行摘要", content="存在高风险事项。", citations=[], risk_level="HIGH")
    ]
    service.legal_retriever.retrieve_for_gaps = lambda gaps: {
        service.legal_retriever._gap_key(gap, idx): [  # noqa: SLF001
            {
                "source": f"GAP:{gap.domain}:{idx}",
                "source_id": "us_cpra",
                "source_title": "California Consumer Privacy Act / CPRA",
                "article_no": "1798.121",
                "display_label": f"CPRA §1798.121 GAP:{gap.domain}:{idx}",
                "snippet": "gap-specific",
                "confidence_score": 0.82,
                "authority_level": "high",
                "binding_force": "mandatory",
                "citation_type": "law_article",
                "source_kind": "law_article",
            }
        ]
        for idx, gap in enumerate(gaps)
    }
    service.legal_retriever.retrieve = lambda domain, extra_context="": [
        {
            "source": f"DOMAIN:{domain}",
            "source_id": "us_cpra",
            "source_title": "California Consumer Privacy Act / CPRA",
            "article_no": "1798.120",
            "display_label": f"CPRA §1798.120 DOMAIN:{domain}",
            "snippet": "domain-level",
            "confidence_score": 0.71,
            "authority_level": "high",
            "binding_force": "mandatory",
            "citation_type": "law_article",
            "source_kind": "law_article",
        }
    ]

    result = service.generate_report(payload)

    assert result.gap_items
    assert all(item.citations for item in result.gap_items)
    assert any(citation.startswith("CIT-US-CPRA-ART1798_121-") for item in result.gap_items for citation in item.citations)
    assert any(ref.display_label.startswith("CPRA §1798.121") for item in result.gap_items for ref in item.citation_refs)
    assert any(ref.confidence_score >= 0.7 for item in result.gap_items for ref in item.citation_refs)
