from backend.domains.cn.transfer_diagnosis.report_renderer import DiagnosisReportRenderer


def test_diagnosis_html_preserves_markdown_blocks_and_escapes_html() -> None:
    html = DiagnosisReportRenderer._build_html_doc(
        "诊断报告",
        [
            (
                "结论",
                "### 依据\n\n- 第一项\n- 第二项\n\n"
                "| 项目 | 状态 |\n| --- | --- |\n| 传输 | 高风险 |\n\n"
                "---\n\n<script>alert(1)</script>",
            )
        ],
    )

    assert "<h2>结论</h2>" in html
    assert "<h3>依据</h3>" in html
    assert "<ul>" in html
    assert "<table>" in html
    assert "<hr />" in html
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
