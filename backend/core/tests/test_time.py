from datetime import timedelta

from backend.common.workflow.trace import TraceManifest
from backend.core.time import utc_now, utc_now_naive


def test_utc_now_is_timezone_aware() -> None:
    assert utc_now().utcoffset() == timedelta(0)


def test_naive_utc_helper_preserves_database_contract() -> None:
    assert utc_now_naive().tzinfo is None


def test_trace_manifest_serializes_explicit_utc_offset() -> None:
    manifest = TraceManifest(run_id="run-1", module="diagnosis")

    assert manifest.created_at.endswith("+00:00")
