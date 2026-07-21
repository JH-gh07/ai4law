from backend.common.runtime.module_run import finalize_run, prepare_run


def test_finalize_run_writes_trace_manifest_after_context_reset(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    trace, token = prepare_run(module="ut", task_id="trace-manifest")
    trace.record("status", {"summary": "started"})

    finalize_run(token)

    assert (trace.trace_dir / "manifest.json").exists()
