"""task082 Feature Flag 与安全默认值。

§9.1：默认关闭；非法配置不得静默转为 active，应回到 canonical 并记录配置错误。
"""

from __future__ import annotations

from enum import Enum
from typing import Mapping

from pydantic import BaseModel, ConfigDict

from backend.common.title_plan.models import ArtifactRole


class TitlePlanMode(str, Enum):
    CANONICAL = "canonical"
    SHADOW = "shadow"
    ACTIVE = "active"


class FailPolicy(str, Enum):
    FALLBACK = "fallback"
    FAIL_CLOSED_CORE = "fail_closed_core"


class TitlePlanConfig(BaseModel):
    """已解析、安全的标题计划配置。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    mode: TitlePlanMode = TitlePlanMode.CANONICAL
    fail_policy: FailPolicy = FailPolicy.FALLBACK
    modules: tuple[str, ...] = ()
    artifact_roles: tuple[ArtifactRole, ...] = ()
    config_errors: tuple[str, ...] = ()

    def effective_mode(self) -> TitlePlanMode:
        """非法配置或未启用时永远回到 canonical。"""
        if not self.enabled:
            return TitlePlanMode.CANONICAL
        if self.config_errors:
            return TitlePlanMode.CANONICAL
        return self.mode


def _parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True", "on", "yes"):
        return True
    if value in (0, "0", "false", "False", "off", "no"):
        return False
    return None


def parse_config(raw: Mapping[str, object] | None) -> TitlePlanConfig:
    """从环境变量风格 mapping 解析配置，非法值回退 canonical 并记录错误。"""
    raw = raw or {}
    errors: list[str] = []

    enabled_raw = raw.get("TITLE_PLAN_ENABLED", 0)
    enabled = _parse_bool(enabled_raw)
    if enabled is None:
        errors.append(f"TITLE_PLAN_ENABLED 非法值 {enabled_raw!r}，回退为 0")
        enabled = False

    mode_raw = raw.get("TITLE_PLAN_MODE", "canonical")
    try:
        mode = TitlePlanMode(str(mode_raw).strip().lower())
    except ValueError:
        errors.append(f"TITLE_PLAN_MODE 非法值 {mode_raw!r}，回退为 canonical")
        mode = TitlePlanMode.CANONICAL

    fail_raw = raw.get("TITLE_PLAN_FAIL_POLICY", "fallback")
    try:
        fail_policy = FailPolicy(str(fail_raw).strip().lower())
    except ValueError:
        errors.append(f"TITLE_PLAN_FAIL_POLICY 非法值 {fail_raw!r}，回退为 fallback")
        fail_policy = FailPolicy.FALLBACK

    modules = _parse_string_list(raw.get("TITLE_PLAN_MODULES"))
    roles: list[ArtifactRole] = []
    for role_raw in _parse_string_list(raw.get("TITLE_PLAN_ARTIFACT_ROLES")):
        try:
            roles.append(ArtifactRole(role_raw.strip().lower()))
        except ValueError:
            errors.append(f"TITLE_PLAN_ARTIFACT_ROLES 非法值 {role_raw!r}，忽略该项")

    return TitlePlanConfig(
        enabled=enabled,
        mode=mode,
        fail_policy=fail_policy,
        modules=tuple(modules),
        artifact_roles=tuple(roles),
        config_errors=tuple(errors),
    )


def _parse_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


DEFAULT_CONFIG = parse_config({})

__all__ = [
    "DEFAULT_CONFIG",
    "FailPolicy",
    "TitlePlanConfig",
    "TitlePlanMode",
    "parse_config",
]
