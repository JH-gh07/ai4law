"""Feature Flag 安全默认值测试。"""

from __future__ import annotations

from backend.common.title_plan import (
    DEFAULT_CONFIG,
    FailPolicy,
    TitlePlanMode,
    parse_config,
)


def test_defaults_disabled_canonical():
    assert DEFAULT_CONFIG.enabled is False
    assert DEFAULT_CONFIG.effective_mode() == TitlePlanMode.CANONICAL
    assert DEFAULT_CONFIG.fail_policy == FailPolicy.FALLBACK
    assert DEFAULT_CONFIG.modules == ()
    assert DEFAULT_CONFIG.artifact_roles == ()


def test_invalid_mode_falls_back_to_canonical():
    cfg = parse_config({"TITLE_PLAN_ENABLED": 1, "TITLE_PLAN_MODE": "aggressive"})
    assert cfg.effective_mode() == TitlePlanMode.CANONICAL
    assert any("TITLE_PLAN_MODE" in e for e in cfg.config_errors)


def test_invalid_role_ignored_and_recorded():
    cfg = parse_config({"TITLE_PLAN_ARTIFACT_ROLES": "docx,not_a_role,pdf"})
    assert "not_a_role" not in [r.value for r in cfg.artifact_roles]
    assert any("TITLE_PLAN_ARTIFACT_ROLES" in e for e in cfg.config_errors)


def test_enabled_active_valid():
    cfg = parse_config({
        "TITLE_PLAN_ENABLED": 1,
        "TITLE_PLAN_MODE": "active",
        "TITLE_PLAN_FAIL_POLICY": "fail_closed_core",
    })
    assert cfg.effective_mode() == TitlePlanMode.ACTIVE
    assert cfg.fail_policy == FailPolicy.FAIL_CLOSED_CORE


def test_disabled_never_active_even_if_mode_active():
    cfg = parse_config({"TITLE_PLAN_ENABLED": 0, "TITLE_PLAN_MODE": "active"})
    assert cfg.effective_mode() == TitlePlanMode.CANONICAL


def test_modules_parsed():
    cfg = parse_config({"TITLE_PLAN_MODULES": "pipia, review"})
    assert cfg.modules == ("pipia", "review")
