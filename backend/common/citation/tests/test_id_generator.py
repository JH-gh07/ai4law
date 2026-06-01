from backend.common.citation.id_generator import generate_citation_id, resolve_abbreviation


def test_generate_citation_id_with_article() -> None:
    cid = generate_citation_id("CN", "PIPL", "39", 1)
    assert cid == "CIT-CN-PIPL-ART39-P01"


def test_generate_citation_id_without_article() -> None:
    cid = generate_citation_id("CN", "PIPL", "", 1)
    assert cid == "CIT-CN-PIPL-GEN-P01"


def test_generate_citation_id_pads_sequence() -> None:
    cid = generate_citation_id("CN", "DSL", "21", 12)
    assert cid == "CIT-CN-DSL-ART21-P12"


def test_resolve_abbreviation_exact_match() -> None:
    assert resolve_abbreviation("个人信息保护法") == "PIPL"
    assert resolve_abbreviation("数据安全法") == "DSL"
    assert resolve_abbreviation("网络安全法") == "CSL"


def test_resolve_abbreviation_with_bookmarks() -> None:
    assert resolve_abbreviation("《个人信息保护法》") == "PIPL"
    assert resolve_abbreviation("《数据出境安全评估办法》") == "EXPORT-ASSESSMENT"


def test_resolve_abbreviation_substring_match() -> None:
    assert resolve_abbreviation("个人信息保护法（2021）") == "PIPL"


def test_resolve_abbreviation_fallback() -> None:
    result = resolve_abbreviation("某未知法规")
    # For titles without recognizable abbreviations, fallback to UNKNOWN or derived chars
    assert len(result) >= 2
