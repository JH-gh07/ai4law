from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = ROOT / "doc" / "knowledge"

NEW_INDEX_DIR = KNOWLEDGE_ROOT / "_index"
NEW_REGISTRY_DIR = KNOWLEDGE_ROOT / "_registry"
NEW_EVALUATION_DIR = KNOWLEDGE_ROOT / "_evaluation"


def sources_csv_path() -> Path:
    return NEW_INDEX_DIR / "sources.csv"


def practice_cases_csv_path() -> Path:
    return NEW_INDEX_DIR / "practice_cases.csv"


def module_catalog_path() -> Path:
    return NEW_INDEX_DIR / "module_catalog.v1.json"


def spec_asset_manifest_path() -> Path:
    return NEW_INDEX_DIR / "spec_asset_manifest.csv"


def source_registry_path() -> Path:
    return NEW_REGISTRY_DIR / "source_registry.v1.json"


def regulation_articles_jsonl_path() -> Path:
    return NEW_REGISTRY_DIR / "regulation_articles.jsonl"


def regulation_article_schema_path() -> Path:
    return NEW_REGISTRY_DIR / "regulation_article.schema.json"
