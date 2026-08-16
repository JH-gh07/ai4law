import json

from backend.common.knowledge import registry as registry_module
from backend.schemas.knowledge import KnowledgeSyncMeta
from backend.services.knowledge_index import get_knowledge_sync_meta


def test_module_catalog_uses_static_file_when_present() -> None:
    catalog = registry_module.load_module_catalog()
    assert "modules" in catalog
    assert "cn_assessment" in catalog["modules"]
    assert "default_usage_scopes" in catalog["modules"]["cn_review"]
    assert "eu_scc" in catalog["modules"]
    assert "us_14117" in catalog["modules"]


def test_module_catalog_rebuilds_when_missing(tmp_path, monkeypatch) -> None:
    module_catalog = tmp_path / "module_catalog.v1.json"
    monkeypatch.setattr(registry_module, "MODULE_CATALOG_PATH", module_catalog)
    monkeypatch.setattr(registry_module, "REGISTRY_DIR", tmp_path)
    catalog = registry_module.load_module_catalog()
    assert module_catalog.exists()
    loaded = json.loads(module_catalog.read_text(encoding="utf-8"))
    assert loaded["modules"]["cn_diagnosis"]["indexes"] == ["workflow_index_cn", "legal_index_cn"]
    assert catalog["modules"]["cn_assessment"]["stages"][-1] == "evaluation"


def test_knowledge_sync_meta_accepts_module_catalog_fields() -> None:
    meta = KnowledgeSyncMeta.model_validate(get_knowledge_sync_meta(cache_refreshed=False))
    assert meta.module_catalog_path.endswith("module_catalog.v1.json")


def test_module_catalog_marks_non_cn_modules_as_disabled_by_default() -> None:
    catalog = registry_module.load_module_catalog()
    assert catalog["modules"]["eu_scc"]["production_enabled"] is False
    assert catalog["modules"]["us_vendor_review"]["production_enabled"] is False


def test_source_registry_respects_declared_gdpr_binding_force() -> None:
    entries = {
        item.source_id: item
        for item in registry_module.build_source_registry_from_sources_csv()
    }

    assert entries["EU-LAW-001"].binding_force == "mandatory"


def test_template_assets_are_structure_only_not_legal_authority() -> None:
    entries = registry_module.build_source_registry_from_sources_csv()
    templates = [
        entry for entry in entries
        if (entry.metadata or {}).get("doc_type") == "template"
    ]

    assert templates
    for entry in templates:
        assert entry.can_be_cited is False, entry.source_id
        assert entry.can_enter_external_report is False, entry.source_id
        assert list(entry.allowed_usage) == ["structure_control", "internal_review"], entry.source_id


def test_source_kind_maps_new_doc_type_enums() -> None:
    # ``policy`` and ``technical_standard`` are newer doc_type values introduced for
    # the JP/KR remediation. They must map onto the stable SourceKind vocabulary
    # (official_guide / standard_clause) so retrieval/citation policy keeps working
    # without a SourceKind Literal expansion.
    assert registry_module._source_kind_from_row(
        {"title": "日本个人信息保护基本方针", "doc_type": "policy", "category": ""}
    ) == "official_guide"
    assert registry_module._source_kind_from_row(
        {"title": "韩国个人信息安全措施标准", "doc_type": "technical_standard", "category": ""}
    ) == "standard_clause"
