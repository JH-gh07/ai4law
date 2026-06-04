from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = ROOT / "doc" / "knowledge"

LEGACY_INDEX_DIR = KNOWLEDGE_ROOT / "index"
LEGACY_REGISTRY_DIR = KNOWLEDGE_ROOT / "registry"
LEGACY_NORMALIZED_DIR = KNOWLEDGE_ROOT / "normalized"
LEGACY_EVALUATION_DIR = KNOWLEDGE_ROOT / "evaluation"

NEW_INDEX_DIR = KNOWLEDGE_ROOT / "_index"
NEW_REGISTRY_DIR = KNOWLEDGE_ROOT / "_registry"
NEW_EVALUATION_DIR = KNOWLEDGE_ROOT / "_evaluation"


def prefer_existing(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def sources_csv_path() -> Path:
    return prefer_existing(
        NEW_INDEX_DIR / "sources.csv",
        LEGACY_INDEX_DIR / "sources.csv",
    )


def practice_cases_csv_path() -> Path:
    return prefer_existing(
        NEW_INDEX_DIR / "practice_cases.csv",
        LEGACY_INDEX_DIR / "practice_cases.csv",
    )


def module_catalog_path() -> Path:
    return prefer_existing(
        NEW_INDEX_DIR / "module_catalog.v1.json",
        LEGACY_REGISTRY_DIR / "module_catalog.v1.json",
    )


def source_registry_path() -> Path:
    return prefer_existing(
        NEW_REGISTRY_DIR / "source_registry.v1.json",
        LEGACY_REGISTRY_DIR / "source_registry.v1.json",
    )


def regulation_articles_jsonl_path() -> Path:
    return prefer_existing(
        NEW_REGISTRY_DIR / "regulation_articles.jsonl",
        LEGACY_NORMALIZED_DIR / "regulation_articles.jsonl",
    )


def regulation_article_schema_path() -> Path:
    return prefer_existing(
        NEW_REGISTRY_DIR / "regulation_article.schema.json",
        LEGACY_NORMALIZED_DIR / "regulation_article.schema.json",
    )

