"""v3 → v4 migration reader (task067 T01)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.common.reporting import migrate_v3_document


def _v3_payload() -> dict:
    return {
        "schema_version": "3.0",
        "document_id": "doc-1",
        "report_type": "assessment",
        "metadata": {
            "title": "测试报告",
            "company_name": "测试公司",
            "report_date": "2026-08-13",
            "report_id": "R-1",
        },
        "provenance": {"generated_at": "2026-08-13T00:00:00+00:00"},
        "compiler_version": "0.1.0",
        "prompt_version": "p1",
        "template_version": "t1",
        "model": "test-model",
        "sections": [
            {
                "section_id": "s1",
                "title": "第一节",
                "level": 2,
                "ordinal": "1",
                "reuse_policy": "single_use",
                "blocks": [
                    {"block_id": "s1_b1", "type": "paragraph", "text": "语义段落。"},
                ],
            }
        ],
    }


def test_v3_payload_migrates_to_v4_with_inline_blocks_preserved() -> None:
    doc = migrate_v3_document(_v3_payload())

    assert doc.schema_version == "4.0"
    assert doc.document_id == "doc-1"
    assert doc.report_type == "assessment"
    assert doc.migrated_from_schema == "3.0"
    assert doc.identity is not None and doc.identity.document_id == "doc-1"
    assert doc.lifecycle is not None
    assert doc.sections[0].blocks[0].type == "paragraph"
    assert doc.sections[0].blocks[0].block_id == "s1_b1"
    assert doc.findings == []
    assert doc.actions == []


def test_v3_payload_accepts_json_string() -> None:
    import json

    doc = migrate_v3_document(json.dumps(_v3_payload()))
    assert doc.document_id == "doc-1"


def test_non_v3_schema_version_is_rejected() -> None:
    payload = _v3_payload()
    payload["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="unsupported schema_version"):
        migrate_v3_document(payload)


def test_v4_payload_is_explicitly_rejected_by_v3_reader() -> None:
    payload = _v3_payload()
    payload["schema_version"] = "4.0"
    with pytest.raises(ValueError):
        migrate_v3_document(payload)


def test_non_dict_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="dict or JSON string"):
        migrate_v3_document(["not", "a", "dict"])  # type: ignore[arg-type]
