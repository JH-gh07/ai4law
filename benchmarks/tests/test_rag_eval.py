from __future__ import annotations

import sqlite3
from pathlib import Path

from benchmarks.smoke_eval import _load_eval_cases, _recall, run_all_evals, run_generation_eval, run_retrieval_eval

ROOT = Path(__file__).resolve().parents[2]


def _runtime_snapshot() -> tuple[set[str], set[str], int]:
    traces = {path.name for path in (ROOT / "storage/traces").glob("*")}
    reports = {path.name for path in (ROOT / "outputs/assessment").glob("*")}
    database = ROOT / "storage/ai4law.db"
    if not database.exists():
        return traces, reports, 0
    with sqlite3.connect(database) as connection:
        count = connection.execute("SELECT COUNT(*) FROM citation_audit_log").fetchone()[0]
    return traces, reports, int(count)


def test_product_smoke_case_schema_and_counts() -> None:
    assert len(_load_eval_cases("retrieval", "all")) == 17
    assert len(_load_eval_cases("generation", "all")) == 14


def test_issue_recall_requires_matching_gold_identifier() -> None:
    assert _recall({"expected-issue"}, {"different-issue"}) == 0.0


def test_retrieval_eval_runs_and_reports_metrics() -> None:
    result = run_retrieval_eval(target="cn")
    assert result["case_count"] == 10
    assert "Recall@K" in result
    assert "MRR" in result
    assert "Forbidden-layer retrieval rate" in result
    review_case = next(item for item in result["results"] if item["case_id"] == "RET-CN-REVIEW-001")
    assert review_case["retrieved_source_ids"][0].startswith("STD-CN-")
    assert len(review_case["retrieved_source_ids"]) == len(set(review_case["retrieved_source_ids"]))


def test_generation_eval_isolated_from_shared_runtime() -> None:
    before = _runtime_snapshot()
    result = run_generation_eval(target="cn")
    after = _runtime_snapshot()
    assert result["case_count"] == 10
    assert before == after
    assert "Issue recall" in result
    assert "Citation correctness" in result
    assert "Forbidden-source leakage rate" in result
    review_results = [item for item in result["results"] if item["case_id"].startswith("GEN-CN-REVIEW-")]
    assert any(item["issue_recall"] > 0 for item in review_results)
    assert any(item["citation_correctness"] > 0 for item in review_results)


def test_run_all_evals_returns_both_sections() -> None:
    result = run_all_evals(target="cn")
    assert "retrieval" in result
    assert "generation" in result


def test_eu_retrieval_eval_runs() -> None:
    result = run_retrieval_eval(target="eu")
    assert result["target"] == "eu"
    assert result["case_count"] == 4
    assert result["Cross-jurisdiction contamination rate"] == 0.0


def test_eu_generation_eval_runs_without_false_issue_match() -> None:
    result = run_generation_eval(target="eu")
    assert result["target"] == "eu"
    assert result["case_count"] == 2
    assert result["Issue recall"] == 0.0
    assert result["Citation correctness"] > 0


def test_us_retrieval_eval_runs() -> None:
    result = run_retrieval_eval(target="us")
    assert result["target"] == "us"
    assert result["case_count"] == 3
    assert result["Recall@K"] > 0
    assert result["Cross-jurisdiction contamination rate"] == 0.0


def test_us_generation_eval_runs_without_false_issue_match() -> None:
    result = run_generation_eval(target="us")
    assert result["target"] == "us"
    assert result["case_count"] == 2
    assert result["Issue recall"] == 0.0
    assert result["Citation correctness"] > 0