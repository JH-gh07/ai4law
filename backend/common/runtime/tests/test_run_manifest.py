from backend.common.runtime.run_manifest import summarize_input, summarize_output, summarize_trace
from backend.common.trace.recorder import TraceRecorder


def test_string_uploaded_files_are_visible_without_copying_file_content() -> None:
    summary = summarize_input(
        {
            "company_name": "Sensitive Co",
            "uploaded_files": [
                "storage://uploads/contract.docx",
                "/tmp/evidence.pdf",
            ],
        }
    )

    assert summary["artifacts"] == [
        {
            "file_name": "contract.docx",
            "storage_uri": "storage://uploads/contract.docx",
        },
        {"file_name": "evidence.pdf", "storage_uri": "/tmp/evidence.pdf"},
    ]
    assert "Sensitive Co" not in str(summary)


def test_output_summary_deduplicates_report_path_and_typed_output() -> None:
    summary = summarize_output(
        {
            "report_path": "/tmp/report.docx",
            "output_files": {
                "docx": "/tmp/report.docx",
                "pdf": "/tmp/report.pdf",
            },
        }
    )

    assert summary["artifacts"] == [
        {"role": "docx", "path": "/tmp/report.docx"},
        {"role": "pdf", "path": "/tmp/report.pdf"},
    ]


def test_trace_summary_reads_canonical_nested_llm_usage(tmp_path) -> None:
    recorder = TraceRecorder(tmp_path / "trace", task_id="task-1")
    recorder.record(
        "tool_result",
        {
            "summary": "model returned",
            "detail": {
                "llm": {
                    "prompt_tokens": 13,
                    "completion_tokens": 5,
                    "total_tokens": 18,
                    "usage_source": "provider",
                    "fallback": False,
                }
            },
        },
    )

    summary = summarize_trace(recorder)

    assert summary["llm_calls"] == 1
    assert summary["tokens"] == {
        "prompt_tokens": 13,
        "completion_tokens": 5,
        "total_tokens": 18,
    }
