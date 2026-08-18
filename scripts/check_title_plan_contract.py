#!/usr/bin/env python3
"""task082 资产同步门禁：Schema/模板/规则/Manifest 一致性检查。

§11.6 至少检查：
  1. Schema 与 Pydantic 字段/闭集枚举一致；
  2. 模板 module/role/version 唯一；
  3. 模板 title_policy 已登记（未就绪模板除外）；
  4. 规则 ID（S1-S9/M1-M5/T1-T8）在实现/文档/测试中均有引用；
  5. Manifest 的 artifact role 属于公共闭集 enum（OUT_OF_SCOPE 例外）；
  6. task080 声明的路径真实存在；
  7. 新增 reason/role/policy 已同步到 Schema 与规则文档；
  8. diagnosis 未完成稳定 ID 前不得 active 接入。

退出码：0 = 全部通过；非 0 = 存在 drift/阻断项。
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.common.title_plan.models import (  # noqa: E402
    ArtifactRole,
    FallbackReason,
    NodeValidationStatus,
    PlanSectionDraft,
    PlanValidationStatus,
    PurposeCode,
    TitlePlanDraft,
    TitlePolicy,
    TitleSource,
)
from backend.common.title_plan.policies import ALL_RULE_IDS  # noqa: E402

TASK080 = ROOT / "status" / "check" / "task080"
SCHEMA_PATH = TASK080 / "title_plan.schema.json"
RULES_PATH = TASK080 / "title_plan_validation_rules.md"
POLICY_MATRIX_PATH = TASK080 / "title_policy_matrix.md"
TEMPLATE_DIR = TASK080 / "template_specs"
MANIFEST_PATH = ROOT / "benchmarks" / "manifests" / "issue078_module_eval_manifest.json"

SPECIAL_ROLE = "OUT_OF_SCOPE"
NOT_READY_VERSIONS = {"", "N/A", "OUT_OF_SCOPE"}


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Schema ↔ Pydantic
# ─────────────────────────────────────────────────────────────────────────────

def check_schema_pydantic(c: Checker, schema: dict) -> None:
    _check_enum(c, "artifact_role", _schema_enum(schema, "artifact_role"),
                {r.value for r in ArtifactRole})
    _check_enum(c, "fallback_reason", _schema_enum(schema, "fallback_reason"),
                {r.value for r in FallbackReason})
    _check_enum(c, "purpose_code", _schema_defs_enum(schema, "purpose_code"),
                {p.value for p in PurposeCode})
    _check_enum(c, "title_source", _schema_defs_enum(schema, "section_title", "title_source"),
                {s.value for s in TitleSource})
    _check_enum(c, "node_validation.status",
                _schema_defs_enum(schema, "section_title", "validation", "status"),
                {s.value for s in NodeValidationStatus})
    _check_enum(c, "validation_result",
                _schema_defs_enum(schema, "audit_record", "validation_result"),
                {s.value for s in PlanValidationStatus})

    _check_field_sync(
        c,
        {name for name in TitlePlanDraft.model_fields},
        set(schema.get("properties", {}).keys()),
        where="root",
    )
    section_props = schema.get("$defs", {}).get("section_title", {}).get("properties", {})
    _check_field_sync(
        c,
        {name for name in PlanSectionDraft.model_fields},
        set(section_props.keys()),
        where="section_title",
    )


def _check_enum(c: Checker, label: str, schema_values: set[str], model_values: set[str]) -> None:
    if schema_values != model_values:
        only_schema = sorted(schema_values - model_values)
        only_model = sorted(model_values - schema_values)
        detail = []
        if only_schema:
            detail.append(f"Schema 多出: {only_schema}")
        if only_model:
            detail.append(f"模型多出: {only_model}")
        c.error(f"{label} 闭集枚举漂移 — " + "；".join(detail))


def _check_field_sync(c: Checker, pydantic_fields: set[str], schema_fields: set[str],
                      *, where: str) -> None:
    only_pydantic = sorted(pydantic_fields - schema_fields)
    only_schema = sorted(schema_fields - pydantic_fields)
    if only_pydantic:
        c.error(f"{where} 字段漂移：Pydantic 有但 Schema 缺 {only_pydantic}")
    if only_schema:
        c.error(f"{where} 字段漂移：Schema 有但 Pydantic 缺 {only_schema}")


def _schema_enum(schema: dict, prop: str) -> set[str]:
    node = schema.get("properties", {}).get(prop, {})
    if "$ref" in node:
        return _schema_defs_enum(schema, node["$ref"].split("/")[-1])
    return set(node.get("enum", []))


def _schema_defs_enum(schema: dict, def_name: str, *path: str) -> set[str]:
    node: object = schema.get("$defs", {}).get(def_name, {})
    for key in path:
        if not isinstance(node, dict):
            return set()
        node = node.get("properties", {}).get(key, {})
    if isinstance(node, dict):
        if "enum" in node:
            return set(node["enum"])
        if "$ref" in node:
            return _schema_defs_enum(schema, node["$ref"].split("/")[-1])
    return set()


# ─────────────────────────────────────────────────────────────────────────────
# 2. 模板唯一性与 policy 登记
# ─────────────────────────────────────────────────────────────────────────────

def check_templates(c: Checker) -> None:
    if not TEMPLATE_DIR.is_dir():
        c.error(f"模板目录不存在: {TEMPLATE_DIR}")
        return
    files = sorted(TEMPLATE_DIR.glob("*.json"))
    if not files:
        c.error(f"模板目录为空: {TEMPLATE_DIR}")
        return

    ready_keys: dict[tuple[str, str, str], list[str]] = {}
    for path in files:
        try:
            data = _load_json(path)
        except json.JSONDecodeError as exc:
            c.error(f"模板 JSON 解析失败: {path.name}: {exc}")
            continue
        module_key = str(data.get("module_key", ""))
        role = str(data.get("artifact_role", ""))
        version = str(data.get("template_version", ""))

        if role not in {r.value for r in ArtifactRole} and role != SPECIAL_ROLE:
            c.error(f"模板 artifact_role 未登记: {path.name} -> {role!r}")

        ready = role != SPECIAL_ROLE and version not in NOT_READY_VERSIONS
        if ready:
            for idx, section in enumerate(data.get("sections", [])):
                policy = str(section.get("title_policy", ""))
                if policy not in {p.value for p in TitlePolicy}:
                    c.error(f"模板 title_policy 未登记: {path.name} section[{idx}] -> {policy!r}")
            key = (module_key, role, version)
            ready_keys.setdefault(key, []).append(path.name)

    for key, names in ready_keys.items():
        if len(names) > 1:
            c.error(f"模板不唯一: {key} -> {names}")

    # 同一 (module_key, artifact_role) 的候选（含未就绪版本）不得多于 1
    by_key: dict[tuple[str, str], list[str]] = {}
    for path in files:
        try:
            data = _load_json(path)
        except json.JSONDecodeError:
            continue
        role = str(data.get("artifact_role", ""))
        if role not in {r.value for r in ArtifactRole}:
            continue
        module_key = str(data.get("module_key", ""))
        by_key.setdefault((module_key, role), []).append(path.name)
    for key, names in by_key.items():
        if len(names) > 1:
            c.error(f"模板 (module_key, artifact_role) 多文件候选: {key} -> {names}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. 规则 ID 引用
# ─────────────────────────────────────────────────────────────────────────────

def check_rule_ids(c: Checker) -> None:
    rules_text = RULES_PATH.read_text(encoding="utf-8") if RULES_PATH.is_file() else ""
    if not rules_text:
        c.error(f"规则文档缺失: {RULES_PATH}")
    test_dir = ROOT / "backend" / "common" / "title_plan" / "tests"
    tests_text = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(test_dir.glob("*.py"))
    ) if test_dir.is_dir() else ""

    # 实现引用：policies 定义常量 → validator 实际引用（AST Load 使用，非仅导入）
    import backend.common.title_plan.policies as _policies
    import backend.common.title_plan.validator as _validator
    constant_by_value = {
        getattr(_policies, name): name
        for name in dir(_policies)
        if isinstance(getattr(_policies, name), str) and getattr(_policies, name) in ALL_RULE_IDS
    }

    validator_source = Path(_validator.__file__).read_text(encoding="utf-8")
    tree = ast.parse(validator_source)
    imported_names: set[str] = set()
    loaded_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith(".policies"):
            imported_names.update(alias.name for alias in node.names)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loaded_names.add(node.id)
    actually_used = imported_names & loaded_names

    for rule_id in sorted(ALL_RULE_IDS):
        if rule_id not in rules_text:
            c.error(f"规则 {rule_id} 未在文档 {RULES_PATH.name} 中出现")
        if rule_id not in tests_text:
            c.error(f"规则 {rule_id} 未在测试中出现（无断言引用）")
        cname = constant_by_value.get(rule_id)
        if not cname:
            c.error(f"规则 {rule_id} 未在 policies 中定义常量")
        elif cname not in actually_used:
            c.error(f"规则 {rule_id} 常量 {cname} 在 validator 中仅导入未实际引用")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Manifest role 合法
# ─────────────────────────────────────────────────────────────────────────────

def check_manifest_roles(c: Checker, manifest: dict) -> None:
    valid_roles = {r.value for r in ArtifactRole} | {SPECIAL_ROLE}

    selection = manifest.get("architecture_title_policy", {}).get("artifact_selection", {})
    for module_key, mapping in selection.items():
        if not isinstance(mapping, dict):
            continue
        for field in ("primary", "secondary"):
            value = mapping.get(field)
            items = value if isinstance(value, list) else [value]
            for role in items:
                if role is not None and str(role) not in valid_roles:
                    c.error(f"Manifest artifact_selection.{module_key}.{field} 未登记 role: {role!r}")

    for task in manifest.get("tasks", []):
        arch = task.get("architecture", {})
        role = arch.get("artifact_role_for_architecture")
        if role is not None and str(role) not in valid_roles:
            c.error(f"Manifest task {task.get('task_id')} 未登记 role: {role!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. task080 声明路径存在
# ─────────────────────────────────────────────────────────────────────────────

def check_declared_paths(c: Checker, manifest: dict) -> None:
    for key in ("benchmark_background", "source_fact", "prompt_catalog",
                "title_policy_matrix", "section_catalog", "title_plan_schema"):
        value = manifest.get(key)
        if value and not (ROOT / value).is_file():
            c.error(f"Manifest 声明路径不存在: {key} -> {value}")

    required_files = [
        SCHEMA_PATH,
        RULES_PATH,
        POLICY_MATRIX_PATH,
        TEMPLATE_DIR,
        MANIFEST_PATH,
    ]
    for path in required_files:
        if not path.exists():
            c.error(f"task080 资产缺失: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. 新增 reason/role/policy 同步
# ─────────────────────────────────────────────────────────────────────────────

def check_new_enum_sync(c: Checker, schema: dict) -> None:
    for reason in ("hash_mismatch", "policy_violation"):
        schema_has = reason in _schema_enum(schema, "fallback_reason")
        rules_has = reason in (RULES_PATH.read_text(encoding="utf-8")
                               if RULES_PATH.is_file() else "")
        if not schema_has:
            c.error(f"FallbackReason.{reason} 未同步到 Schema")
        if not rules_has:
            c.error(f"FallbackReason.{reason} 未同步到规则文档")

    for role in ("web", "pdf", "document_ir"):
        if role not in _schema_enum(schema, "artifact_role"):
            c.error(f"ArtifactRole.{role} 未同步到 Schema")


# ─────────────────────────────────────────────────────────────────────────────
# 7. diagnosis 未 active 接入
# ─────────────────────────────────────────────────────────────────────────────

def check_diagnosis_not_active(c: Checker) -> None:
    diagnosis_path = TEMPLATE_DIR / "diagnosis.json"
    if diagnosis_path.is_file():
        data = _load_json(diagnosis_path)
        version = str(data.get("template_version", ""))
        if version not in NOT_READY_VERSIONS:
            c.error("diagnosis 模板已就绪，但稳定 ID 尚未完成（task081），禁止 active 接入")

    from backend.common.title_plan.config import DEFAULT_CONFIG, TitlePlanMode
    if DEFAULT_CONFIG.effective_mode() != TitlePlanMode.CANONICAL:
        c.error("默认配置 effective_mode 不是 canonical，违反安全默认值")


def main() -> int:
    c = Checker()

    if not SCHEMA_PATH.is_file():
        c.error(f"Schema 不存在: {SCHEMA_PATH}")
        return _report(c)

    schema = _load_json(SCHEMA_PATH)
    check_schema_pydantic(c, schema)
    check_templates(c)
    check_rule_ids(c)

    if MANIFEST_PATH.is_file():
        manifest = _load_json(MANIFEST_PATH)
        check_manifest_roles(c, manifest)
        check_declared_paths(c, manifest)
    else:
        c.error(f"Manifest 不存在: {MANIFEST_PATH}")

    check_new_enum_sync(c, schema)
    check_diagnosis_not_active(c)

    return _report(c)


def _report(c: Checker) -> int:
    for msg in c.warnings:
        print(f"WARN  {msg}")
    for msg in c.errors:
        print(f"ERROR {msg}")
    print()
    print(f"contract lint: {len(c.errors)} error(s), {len(c.warnings)} warning(s)")
    return 1 if c.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
