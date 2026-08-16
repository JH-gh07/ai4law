from __future__ import annotations

import csv
import json
from pathlib import Path

from backend.common.knowledge.v2 import SourceRegistryEntry
from backend.common.knowledge.paths import (
    module_catalog_path,
    source_registry_path,
    sources_csv_path,
)

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = source_registry_path().parent
REGISTRY_PATH = source_registry_path()
MODULE_CATALOG_PATH = module_catalog_path()
SOURCES_CSV = sources_csv_path()

# Regional jurisdictions are carried in the catalog/registry for browse-and-cite
# and the dedicated international legal index (`legal_index_intl`). They are NOT
# assigned to any CN/EU/US retrieval module, so regional rows can never pollute
# the default module pools. The `intl-<cc>` module tag in sources.csv is kept as
# `metadata.intl_module` (routing hint) and as a raw `metadata.module` value, but
# it is never promoted into `modules`.
REGIONAL_JURISDICTIONS = frozenset({"jp", "my", "kr", "hk", "vn", "sg", "tw", "mo"})


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
            "production_enabled": True,
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
        "us_14117": {
            "indexes": ["workflow_index_us", "legal_index_us", "standard_clause_index_us", "template_index_us", "testcase_index_us"],
            "stages": ["document_type_detection", "clause_compare", "issue_discovery", "legal_grounding", "report_generation", "evaluation"],
            "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
            "jurisdiction": "us",
            "production_enabled": True,
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
        "us_cpra": {
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
    category = (row.get("category") or "").lower()
    # Templates are structure/format scaffolding, never a citable legal article or
    # a standard clause. Map them to template_slot (the SourceKind paired with
    # L4_template) so they never share a kind with real standard clauses.
    if doc_type == "template":
        return "template_slot"
    # ``doc_type`` is a free-form metadata string; map the newer, finer-grained
    # values (policy, technical_standard) onto the stable SourceKind vocabulary so
    # retrieval/citation policy and Evidence Center labels keep working without a
    # SourceKind Literal expansion. "policy" is an official government statement,
    # closer to official guidance than to a law article; "technical_standard" is a
    # standard/annex, i.e. standard_clause.
    if "指南" in title or "指引" in title or doc_type in {"guide", "policy"}:
        return "official_guide"
    if "模板" in title or "模板" in category:
        return "standard_clause"
    if "标准合同" in title or "标准" in title or "规范" in title or doc_type == "technical_standard":
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


def _binding_force_from_row(row: dict[str, str]) -> str:
    declared = (row.get("binding_force") or "").strip().lower()
    if declared in {"mandatory", "recommended", "reference"}:
        return declared
    return _binding_force_from_title(row.get("title") or "")


def _authority_level_from_row(row: dict[str, str]) -> str:
    normalized = (row.get("authority") or "").lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    level = (row.get("authority_level") or "").lower()
    if level in {"official", "high"}:
        return "high"
    if level in {"medium", "recommended"}:
        return "medium"
    return "low"


def _layer_from_row(row: dict[str, str]) -> str:
    """Derive the knowledge layer for a source row.

    Templates live in ``L4_template`` (structure/format scaffolding, never a
    citable legal basis); everything else in this catalog is a regulatory/legal
    source and belongs in ``L1_regulatory_evidence``. The CSV ``layer`` column uses
    a different vocabulary (``template_assets`` / ``legal_rules`` /
    ``supplemental_assets`` / ...) so we derive from ``doc_type``, the stable
    discriminator, rather than that free-form column.
    """
    if (row.get("doc_type") or "").strip().lower() == "template":
        return "L4_template"
    return "L1_regulatory_evidence"


def _citation_policy_for_row(row: dict[str, str]) -> tuple[bool, bool, list[str]]:
    """Return (can_be_cited, can_enter_external_report, allowed_usage) for a row.

    Sources marked ``metadata_review_required`` are isolated from formal legal
    conclusions and article-number citation until a legal-domain expert signs off
    on their identity (see status/check/task065/jp_kr_source_adjudication.csv).
    They remain browsable in the Evidence Center but are never promoted as a
    citable or external-report basis.
    """
    review_status = (row.get("review_status") or "").strip().lower()
    if review_status == "metadata_review_required":
        return (False, False, ["internal_review"])
    if (row.get("doc_type") or "").strip().lower() == "template":
        return (False, False, ["structure_control", "internal_review"])
    return (True, True, ["legal_grounding", "external_report", "internal_review"])


def _modules_for_row(jurisdiction: str, path: str) -> list[str]:
    if path == "reference":
        return []  # reference-only sources stay out of retrieval pools
    if jurisdiction == "cn":
        modules = ["cn_diagnosis"]
        if path in {"assessment", "all"}:
            modules.append("cn_assessment")
        if path in {"review", "all", "scc"}:
            modules.append("cn_review")
        if path in {"assessment", "all", "pipia"}:
            modules.append("cn_pipia")
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
            modules.append("us_14117")
        if path in {"review", "all", "vendor"}:
            modules.append("us_vendor_review")
        if path in {"review", "all", "privacy"}:
            modules.append("us_cpra")
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
            source_id = (row.get("source_id") or "").strip()
            title = (row.get("title") or "").strip()
            if not source_id or not title:
                continue
            path = (row.get("path") or "all").strip()
            modules = _modules_for_row(jurisdiction, path)
            # `intl-<cc>` tags are international-index routing hints, not retrieval
            # modules. Keep them out of `modules` so regional rows never enter the
            # CN/EU/US module pools, but preserve them for legal_index_intl routing.
            intl_module = ""
            if row.get("module"):
                declared = [item.strip().replace("-", "_") for item in row["module"].split("|") if item.strip()]
                if jurisdiction in REGIONAL_JURISDICTIONS:
                    intl_module = "|".join(declared)
                else:
                    modules = declared
            can_be_cited, can_enter_external_report, allowed_usage = _citation_policy_for_row(row)
            review_status = (row.get("review_status") or "published").strip() or "published"
            entries.append(
                SourceRegistryEntry(
                    source_id=source_id,
                    title=title,
                    aliases=[],
                    jurisdiction=jurisdiction,
                    modules=modules,
                    layer=_layer_from_row(row),
                    source_kind=_source_kind_from_row(row),
                    authority_level=_authority_level_from_row(row),
                    binding_force=_binding_force_from_row(row),
                    status=(row.get("status") or "effective").strip() or "effective",
                    review_status=review_status,
                    allowed_usage=allowed_usage,
                    can_be_cited=can_be_cited,
                    can_enter_external_report=can_enter_external_report,
                    metadata={
                        "path": path,
                        "module": (row.get("module") or "").strip(),
                        "intl_module": intl_module,
                        "category": (row.get("category") or "").strip(),
                        "doc_type": (row.get("doc_type") or "").strip(),
                        "publisher": (row.get("publisher") or "").strip(),
                        "source_org": (row.get("source_org") or "").strip(),
                        "publish_date": (row.get("publish_date") or "").strip(),
                        "effective_date": (row.get("effective_date") or "").strip(),
                        "snapshot_path": (row.get("snapshot_path") or "").strip(),
                        "external_url": (row.get("url") or "").strip(),
                        "usage": (row.get("usage") or "").strip(),
                        "suitable_for": (row.get("suitable_for") or "").strip(),
                        "report_usage": (row.get("report_usage") or "").strip(),
                        "summary": (row.get("summary") or "").strip(),
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
