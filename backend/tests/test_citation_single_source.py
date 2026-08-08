from scripts.check_citation_single_source import check


def test_production_citation_calls_use_single_source_pipeline() -> None:
    assert check() == []
