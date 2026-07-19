"""Canonical paths for repository-owned resources and benchmark datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_ROOT = PROJECT_ROOT / "resources" / "legal"
REPORT_TEMPLATE_ROOT = PROJECT_ROOT / "resources" / "templates"
RULE_ROOT = PROJECT_ROOT / "resources" / "rules"
BENCHMARK_DATASET_ROOT = PROJECT_ROOT / "benchmarks" / "datasets"
PRODUCT_SMOKE_BENCHMARK_ROOT = BENCHMARK_DATASET_ROOT / "product_smoke"
RAG_RETRIEVAL_BENCHMARK_ROOT = BENCHMARK_DATASET_ROOT / "rag_retrieval"



def report_template_path(jurisdiction: Literal["cn", "eu", "us"], file_name: str) -> Path:
    """Return one active report-template path."""

    if Path(file_name).name != file_name:
        raise ValueError("Report template name must not contain directory segments")
    return REPORT_TEMPLATE_ROOT / jurisdiction / file_name


def rule_resource_path(
    jurisdiction: Literal["cn", "eu", "us"],
    file_name: str,
) -> Path:
    """Return one active jurisdiction-specific rule resource path."""

    if Path(file_name).name != file_name:
        raise ValueError("Rule resource name must not contain directory segments")
    return RULE_ROOT / jurisdiction / file_name