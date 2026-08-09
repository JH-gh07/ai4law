import json
from collections import Counter
from pathlib import Path

from backend.common.knowledge.paths import regulation_articles_jsonl_path
from backend.services.knowledge_index import (
    _clean_source_text,
    _normalize_article_lookup_key,
    get_article_detail,
    read_text_preview,
)


def test_clean_source_text_removes_snapshot_artifacts_and_rejoins_lines() -> None:
    raw = (
        "4.5.2016 EN Official Journal of the European Union L 119/1\n"
        "L 119/2\n"
        ". . . . . . . .\n"
        "个人信息出境\n认证活动\n"
        "cross-\nborder transfer\n"
        "<p>第四条&nbsp;处理者应当履行义务。</p>\n"
    )

    cleaned = _clean_source_text(raw)

    assert "Official Journal" not in cleaned
    assert "L 119/2" not in cleaned
    assert ". . ." not in cleaned
    assert "个人信息出境认证活动" in cleaned
    assert "crossborder transfer" in cleaned
    assert "第四条 处理者应当履行义务。" in cleaned


def _registry_rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in regulation_articles_jsonl_path().read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_article_detail_resolves_every_unique_registry_locator() -> None:
    rows = _registry_rows()
    counts = Counter(
        (
            str(row.get("source_id", "")),
            _normalize_article_lookup_key(str(row.get("article_ref", ""))),
        )
        for row in rows
    )
    unique_rows = [
        row
        for row in rows
        if counts[
            (
                str(row.get("source_id", "")),
                _normalize_article_lookup_key(str(row.get("article_ref", ""))),
            )
        ]
        == 1
    ]

    # 2026-08-10 (Phase-4 CPRA dedup): removed 2 contamination entries
    # (US-CA-001-060 outboard-engine junk + US-CA-001-069 content subset),
    # renamed 5 remaining duplicates with unique -N suffixes.
    # Registry is now 100 % unique — every (source_id, article_ref) key
    # resolves to exactly one row. Row count is not a frozen invariant;
    # it shifts whenever a source is cleaned or extended.
    assert len(unique_rows) == len(rows)
    assert len({str(row.get("source_id", "")) for row in unique_rows}) == 102
    for row in unique_rows:
        source_id = str(row["source_id"])
        article_no = _normalize_article_lookup_key(str(row["article_ref"]))
        detail = get_article_detail(source_id, article_no)

        assert detail is not None, (source_id, article_no)
        assert detail["source_id"] == source_id
        assert detail["article_no"] == article_no
        assert detail["article_content"] == str(row["content"]).strip()


def test_article_detail_rejects_an_ambiguous_registry_locator() -> None:
    # Phase-4 dedup: CN-LAW-001 article 23 is now unique (penalty row renamed to
    # "处罚-23-1"). Verify that a non-existent article returns None instead.
    assert get_article_detail("CN-LAW-001", "9999") is None


def test_gdpr_transfer_articles_have_semantic_locators() -> None:
    article_44 = get_article_detail("EU-LAW-001", "44")
    article_46 = get_article_detail("EU-LAW-001", "46")

    assert article_44 is not None
    assert "Any transfer of personal data" in article_44["article_content"]
    assert article_46 is not None
    assert "appropriate safeguards" in article_46["article_content"]
    assert get_article_detail("EU-LAW-001", "段落1") is None


def test_eo14117_rules_have_exact_ecfr_locators() -> None:
    prohibited = get_article_detail("US-FED-001", "202.301")
    restricted = get_article_detail("US-FED-001", "202.401")
    recordkeeping = get_article_detail("US-FED-001", "202.1101")

    assert prohibited is not None
    assert "Prohibited data-brokerage transactions" in prohibited["article_content"]
    assert restricted is not None
    assert "Authorization to conduct restricted transactions" in restricted["article_content"]
    assert recordkeeping is not None
    assert "at least 10 years" in recordkeeping["article_content"]
    assert get_article_detail("US-FED-001", "段落1") is None


def test_read_text_preview_strips_html_markup(tmp_path: Path) -> None:
    snapshot = tmp_path / "source.html"
    snapshot.write_text(
        """<!DOCTYPE html>
<html>
  <head>
    <title>示例</title>
    <style>.hidden { display:none; }</style>
    <script>console.log("ignore")</script>
  </head>
  <body>
    <article>
      <h1>数据出境安全评估办法</h1>
      <p>第四条 处理者向境外提供重要数据，应当申报安全评估。</p>
    </article>
  </body>
</html>
""",
        encoding="utf-8",
    )

    preview = read_text_preview(str(snapshot), limit=200)

    assert "数据出境安全评估办法" in preview
    assert "第四条 处理者向境外提供重要数据，应当申报安全评估。" in preview
    assert "<html>" not in preview.lower()
    assert "<script>" not in preview.lower()
    assert "console.log" not in preview


def test_read_text_preview_prefers_main_content_over_navigation(tmp_path: Path) -> None:
    snapshot = tmp_path / "page.html"
    snapshot.write_text(
        """<!DOCTYPE html>
<html>
  <body>
    <div class="top-nav">首页 | 时政要闻 | 搜索 | 互动服务</div>
    <div class="details-body">
      <div class="trs_editor_view">
        <p>《数据出境安全评估申报指南》适用于申报材料准备与流程说明。</p>
        <p>申报前应当结合处理活动、数据类型和出境必要性开展自评估。</p>
      </div>
    </div>
  </body>
</html>
""",
        encoding="utf-8",
    )

    preview = read_text_preview(str(snapshot), limit=200)

    assert "《数据出境安全评估申报指南》适用于申报材料准备与流程说明。" in preview
    assert "申报前应当结合处理活动、数据类型和出境必要性开展自评估。" in preview
    assert "首页" not in preview
    assert "搜索" not in preview


def test_read_text_preview_skips_css_and_site_metadata(tmp_path: Path) -> None:
    snapshot = tmp_path / "mixed.html"
    snapshot.write_text(
        """<!DOCTYPE html>
<html>
  <body>
    <style>
      .time_dy span { margin-top: 9px; }
    </style>
    <div class="site-title">国家服务业扩大开放综合示范区</div>
    <div class="detail-content">
      <p>北京推出数据跨境便利化服务举措，企业数据出境安全评估用时减半</p>
      <p>市互联网信息办公室发布数据跨境流动便利化实践成果，进一步提升企业申报效率。</p>
      <p>来源：京报网</p>
    </div>
  </body>
</html>
""",
        encoding="utf-8",
    )

    preview = read_text_preview(str(snapshot), limit=220)

    assert "北京推出数据跨境便利化服务举措，企业数据出境安全评估用时减半" in preview
    assert "市互联网信息办公室发布数据跨境流动便利化实践成果" in preview
    assert ".time_dy span" not in preview
    assert "来源：京报网" not in preview
