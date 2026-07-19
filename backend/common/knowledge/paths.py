from __future__ import annotations

from pathlib import Path

from backend.core.resource_paths import KNOWLEDGE_ROOT, RAG_RETRIEVAL_BENCHMARK_ROOT

CATALOG_DIR = KNOWLEDGE_ROOT / "catalog"
REGISTRY_DIR = KNOWLEDGE_ROOT / "registry"
RETRIEVAL_DATASET_DIR = RAG_RETRIEVAL_BENCHMARK_ROOT


def sources_csv_path() -> Path:
    return CATALOG_DIR / "sources.csv"


def practice_cases_csv_path() -> Path:
    return CATALOG_DIR / "practice_cases.csv"


def module_catalog_path() -> Path:
    return CATALOG_DIR / "module_catalog.v1.json"


def spec_asset_manifest_path() -> Path:
    return CATALOG_DIR / "spec_asset_manifest.csv"


def source_registry_path() -> Path:
    return REGISTRY_DIR / "source_registry.v1.json"


def regulation_articles_jsonl_path() -> Path:
    return REGISTRY_DIR / "regulation_articles.jsonl"
