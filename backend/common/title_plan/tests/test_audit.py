"""L3 审计脱敏与恢复测试。"""

from __future__ import annotations

from backend.common.title_plan import (
    redact,
    restore_audit,
    serialize_audit,
    serialize_audit_json,
    verify_audit_hash,
)
from backend.common.title_plan.tests.test_freeze import _valid_outcome


def _frozen(make_snapshot, tmp_path, fixed_sections, ctx):
    from backend.common.title_plan import freeze_title_plan
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    return freeze_title_plan(out, input_hash="ih-1", validator_version="v-1", template=snap)


def test_redact_sensitive_keys():
    data = {"api_key": "sk-abc", "nested": {"Authorization": "Bearer xyz"}, "ok": "标题"}
    out = redact(data)
    assert out["api_key"] == "[REDACTED]"
    assert out["nested"]["Authorization"] == "[REDACTED]"
    assert out["ok"] == "标题"


def test_redact_sensitive_values():
    data = {"model": "gpt-4", "path": "/Users/alice/secret.txt",
           "token": "Bearer abc.def.ghi", "uri": "http://192.168.1.10/internal"}
    out = redact(data)
    assert out["path"] == "[REDACTED]"
    assert out["token"] == "[REDACTED]"
    assert out["uri"] == "[REDACTED]"


def test_serialize_audit_no_token_leak(make_snapshot, tmp_path, fixed_sections, ctx):
    frozen = _frozen(make_snapshot, tmp_path, fixed_sections, ctx)
    text = serialize_audit_json(frozen)
    assert "Bearer" not in text
    assert "/Users/" not in text
    assert "api_key" not in text


def test_serialize_audit_roundtrip(make_snapshot, tmp_path, fixed_sections, ctx):
    frozen = _frozen(make_snapshot, tmp_path, fixed_sections, ctx)
    data = serialize_audit(frozen)
    assert data["template_hash"] == frozen.plan.template_hash
    assert data["validation_status"] in {"pass", "fallback"}
    assert data["frozen_plan_hash"] == frozen.frozen_plan_hash
    assert "nodes" in data
    assert verify_audit_hash(data, frozen_plan_hash=frozen.frozen_plan_hash)


def test_restore_audit_recovers_hash_and_status(make_snapshot, tmp_path, fixed_sections, ctx):
    frozen = _frozen(make_snapshot, tmp_path, fixed_sections, ctx)
    text = serialize_audit_json(frozen)
    data = restore_audit(text)
    assert data["template_hash"] == frozen.plan.template_hash
    assert data["frozen_plan_hash"] == frozen.frozen_plan_hash
    assert data["validator_version"] == "v-1"
