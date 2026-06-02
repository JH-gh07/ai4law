from backend.common.rag.eval import run_all_evals, run_generation_eval, run_retrieval_eval


def test_retrieval_eval_runs_and_reports_metrics() -> None:
    result = run_retrieval_eval()
    assert result["case_count"] >= 10
    assert "Recall@K" in result
    assert "MRR" in result
    assert "Forbidden-layer retrieval rate" in result
    review_case = next(item for item in result["results"] if item["case_id"] == "RET-CN-REVIEW-001")
    assert review_case["retrieved_source_ids"][0].startswith("STD-CN-")
    assert len(review_case["retrieved_source_ids"]) == len(set(review_case["retrieved_source_ids"]))


def test_generation_eval_runs_and_reports_metrics() -> None:
    result = run_generation_eval()
    assert result["case_count"] >= 10
    assert "Issue recall" in result
    assert "Citation correctness" in result
    assert "Forbidden-source leakage rate" in result
    review_results = [item for item in result["results"] if item["case_id"].startswith("GEN-CN-REVIEW-")]
    assert any(item["issue_recall"] > 0 for item in review_results)
    assert any(item["citation_correctness"] > 0 for item in review_results)


def test_run_all_evals_returns_both_sections() -> None:
    result = run_all_evals()
    assert "retrieval" in result
    assert "generation" in result
