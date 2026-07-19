from pathlib import Path

from backend.services.knowledge_index import read_text_preview


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
