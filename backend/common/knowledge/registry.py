from __future__ import annotations

import csv
import json
from pathlib import Path

from backend.common.knowledge.v2 import SourceRegistryEntry

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = ROOT / "doc" / "knowledge" / "registry"
REGISTRY_PATH = REGISTRY_DIR / "source_registry.v1.json"
MODULE_CATALOG_PATH = REGISTRY_DIR / "module_catalog.v1.json"
SOURCES_CSV = ROOT / "doc" / "knowledge" / "index" / "sources.csv"

DEFAULT_MODULE_CATALOG = {
    "version": "v1",
    "modules": {
        "cn_diagnosis": {
            "indexes": ["workflow_index_cn", "legal_index_cn"],
            "stages": ["path_diagnosis", "legal_grounding"],
            "default_usage_scopes": ["internal_review", "legal_grounding"],
            "jurisdiction": "cn",
            "production_enabled": True,
            "requires_standard_clause_index": False,
            "template_policy": "official_only",
        },
        "cn_assessment": {
            "indexes": ["workflow_index_cn", "legal_index_cn", "template_index_cn", "testcase_index_cn"],
            "stages": ["issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "cn",
            "production_enabled": True,
            "requires_standard_clause_index": False,
            "template_policy": "official_only",
        },
        "cn_review": {
            "indexes": ["workflow_index_cn", "legal_index_cn", "standard_clause_index_cn", "template_index_cn", "testcase_index_cn"],
            "stages": ["document_type_detection", "clause_compare", "issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "cn",
            "production_enabled": True,
            "requires_standard_clause_index": True,
            "template_policy": "official_only",
        },
        "eu_scc": {
            "indexes": ["workflow_index_eu", "legal_index_eu", "standard_clause_index_eu", "template_index_eu", "testcase_index_eu"],
            "stages": ["document_type_detection", "clause_compare", "issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "eu",
            "production_enabled": False,
            "requires_standard_clause_index": True,
            "template_policy": "official_only",
        },
        "eu_bcr": {
            "indexes": ["workflow_index_eu", "legal_index_eu", "standard_clause_index_eu", "template_index_eu", "testcase_index_eu"],
            "stages": ["document_type_detection", "clause_compare", "issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "eu",
            "production_enabled": False,
            "requires_standard_clause_index": True,
            "template_policy": "official_only",
        },
        "eu_dpia": {
            "indexes": ["workflow_index_eu", "legal_index_eu", "template_index_eu", "testcase_index_eu"],
            "stages": ["issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "eu",
            "production_enabled": False,
            "requires_standard_clause_index": False,
            "template_policy": "official_only",
        },
        "eu_tia": {
            "indexes": ["workflow_index_eu", "legal_index_eu", "template_index_eu", "testcase_index_eu"],
            "stages": ["issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "eu",
            "production_enabled": False,
            "requires_standard_clause_index": False,
            "template_policy": "official_only",
        },
        "us_eo14117": {
            "indexes": ["workflow_index_us", "legal_index_us", "standard_clause_index_us", "template_index_us", "testcase_index_us"],
            "stages": ["document_type_detection", "clause_compare", "issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "us",
            "production_enabled": False,
            "requires_standard_clause_index": True,
            "template_policy": "official_only",
        },
        "us_vendor_review": {
            "indexes": ["workflow_index_us", "legal_index_us", "standard_clause_index_us", "template_index_us", "testcase_index_us"],
            "stages": ["document_type_detection", "clause_compare", "issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "us",
            "production_enabled": False,
            "requires_standard_clause_index": True,
            "template_policy": "official_only",
        },
        "us_privacy_review": {
            "indexes": ["workflow_index_us", "legal_index_us", "standard_clause_index_us", "template_index_us", "testcase_index_us"],
            "stages": ["document_type_detection", "clause_compare", "issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "us",
            "production_enabled": False,
            "requires_standard_clause_index": True,
            "template_policy": "official_only",
        },
    },
}


def _source_kind_from_row(row: dict[str, str]) -> str:
    title = (row.get("title") or "").replace("《", "").replace("》", "")
    doc_type = (row.get("doc_type") or "").lower()
    if "指南" in title or "指引" in title or doc_type == "guide":
        return "official_guide"
    if "标准合同" in title or "标准" in title or "规范" in title:
        return "standard_clause"
    return "law_article"


def _binding_force_from_title(title: str) -> str:
    clean = (title or "").replace("《", "").replace("》", "")
    if "法" in clean and "办法" not in clean:
        return "mandatory"
    if any(token in clean for token in ("办法", "条例", "规定")):
        return "mandatory"
    if any(token in clean for token in ("指南", "标准", "规范")):
        return "recommended"
    return "reference"


def _authority_level_from_row(row: dict[str, str]) -> str:
    level = (row.get("authority_level") or "").lower()
    if level in {"official", "high"}:
        return "high"
    if level in {"medium", "recommended"}:
        return "medium"
    return "low"


def _modules_for_row(jurisdiction: str, path: str) -> list[str]:
    if jurisdiction == "cn":
        modules = ["cn_diagnosis"]
        if path in {"assessment", "all"}:
            modules.append("cn_assessment")
        if path in {"review", "all", "scc"}:
            modules.append("cn_review")
        return modules
    if jurisdiction == "eu":
        modules: list[str] = []
        if path in {"review", "all", "scc"}:
            modules.append("eu_scc")
        if path in {"review", "all", "bcr"}:
            modules.append("eu_bcr")
        if path in {"assessment", "all", "dpia"}:
            modules.append("eu_dpia")
        if path in {"assessment", "all", "tia"}:
            modules.append("eu_tia")
        return modules or ["eu_scc"]
    if jurisdiction == "us":
        modules: list[str] = []
        if path in {"review", "all", "eo14117"}:
            modules.append("us_eo14117")
        if path in {"review", "all", "vendor"}:
            modules.append("us_vendor_review")
        if path in {"review", "all", "privacy"}:
            modules.append("us_privacy_review")
        return modules or ["us_vendor_review"]
    return []


def build_source_registry_from_sources_csv() -> list[SourceRegistryEntry]:
    if not SOURCES_CSV.exists():
        return []

    entries: list[SourceRegistryEntry] = []
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            jurisdiction = (row.get("jurisdiction") or "").strip().lower()
            if jurisdiction not in {"cn", "eu", "us"}:
                continue
            source_id = (row.get("source_id") or "").strip()
            title = (row.get("title") or "").strip()
            if not source_id or not title:
                continue
            path = (row.get("path") or "all").strip()
            modules = _modules_for_row(jurisdiction, path)
            entries.append(
                SourceRegistryEntry(
                    source_id=source_id,
                    title=title,
                    aliases=[],
                    jurisdiction=jurisdiction,
                    modules=modules,
                    layer="L1_regulatory_evidence",
                    source_kind=_source_kind_from_row(row),
                    authority_level=_authority_level_from_row(row),
                    binding_force=_binding_force_from_title(title),
                    status=(row.get("status") or "effective").strip() or "effective",
                    review_status="published",
                    allowed_usage=["legal_grounding", "external_report", "internal_review"],
                    can_be_cited=True,
                    can_enter_external_report=True,
                    metadata={
                        "path": path,
                        "doc_type": (row.get("doc_type") or "").strip(),
                        "source_org": (row.get("source_org") or "").strip(),
                        "publish_date": (row.get("publish_date") or "").strip(),
                        "effective_date": (row.get("effective_date") or "").strip(),
                        "snapshot_path": (row.get("snapshot_path") or "").strip(),
                        "source_url": (row.get("url") or "").strip(),
                    },
                )
            )
    return entries


def ensure_source_registry() -> list[SourceRegistryEntry]:
    if REGISTRY_PATH.exists():
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return [SourceRegistryEntry.model_validate(item) for item in raw.get("entries", [])]

    entries = build_source_registry_from_sources_csv()
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_from": str(SOURCES_CSV),
                "entries": [entry.model_dump() for entry in entries],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return entries


def load_module_catalog() -> dict:
    if MODULE_CATALOG_PATH.exists():
        return json.loads(MODULE_CATALOG_PATH.read_text(encoding="utf-8"))
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    MODULE_CATALOG_PATH.write_text(
        json.dumps(DEFAULT_MODULE_CATALOG, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return dict(DEFAULT_MODULE_CATALOG)
