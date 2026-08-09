import json
from collections import Counter
from pathlib import Path

from backend.common.knowledge.paths import regulation_articles_jsonl_path
from backend.services.knowledge_index import (
    _normalize_article_lookup_key,
    get_article_detail,
    read_text_preview,
)


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

    # Count updated 2026-08-08: CN-REG-004 replaced 9 web-noise records with
    # 20 formal articles (commit 979d714), raising unique_rows from 1602 → 1613.
    # Count updated 2026-08-08 (P2 fix): 1347 regional-law articles re-ingested with
    # correct field names (article_ref/content), raising unique_rows 1613 → 2960
    # and source_ids 69 → 102.
    # Count updated 2026-08-08 (Phase-4): 36 enforcement-provision rows renamed to
    # "处罚-{art}-{n}" so every (source_id, article_no) key is now unique.
    # Before the 2026-08-09 EDPB cleanup, unique_rows == total_rows == 3030.
    # Metadata/heading fallback rows were replaced by semantic Step 1/Step 3
    # chunks, reducing the canonical registry to 3026 unique rows.
    # 2026-08-09: registry grew to 3035 (5 new articles added, e.g. supplemental
    # EDPB guidance paragraphs), raising the canonical count to 3031.
    assert len(unique_rows) == 3035
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
