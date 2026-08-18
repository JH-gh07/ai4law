"""task082 模板加载、版本/hash 与不可变快照。

加载顺序（§5.1）：role 闭集 → 读取唯一文件 → Schema 校验 → 内容 lint
（ID/parent/order/purpose/policy）→ canonicalize → template_hash → 不可变快照。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from backend.common.title_plan.canonical import canonical_json, stable_hash
from backend.common.title_plan.errors import ErrorCode, TitlePlanError
from backend.common.title_plan.models import (
    ArtifactRole,
    PurposeCode,
    SectionSpec,
    TemplateSnapshot,
    TemplateSpec,
    TitlePolicy,
)
from backend.common.title_plan.policies import derive_purpose_code

DEFAULT_TEMPLATE_DIR = (
    Path(__file__).resolve().parents[3]
    / "status"
    / "check"
    / "task080"
    / "template_specs"
)


def _iter_template_files(template_dir: Path) -> Iterable[Path]:
    if not template_dir.is_dir():
        return []
    return sorted(p for p in template_dir.glob("*.json") if p.is_file())


def _read_raw(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise TitlePlanError(
            ErrorCode.TEMPLATE_SCHEMA_INVALID, f"模板 JSON 解析失败: {path.name}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise TitlePlanError(
            ErrorCode.TEMPLATE_SCHEMA_INVALID, f"模板根必须是对象: {path.name}"
        )
    return data


def _lint_sections(raw_sections: list[dict]) -> list[str]:
    """内容 lint：ID/parent/order/level/purpose/policy/required 一致性。"""
    errors: list[str] = []
    ids: list[str] = []
    for raw in raw_sections:
        sid = str(raw.get("section_id", "")).strip()
        if not sid:
            errors.append("section_id 为空")
            continue
        if sid in ids:
            errors.append(f"section_id 重复: {sid}")
        ids.append(sid)

    id_set = set(ids)
    for raw in raw_sections:
        sid = str(raw.get("section_id", "")).strip()
        parent = raw.get("parent_id")
        if parent is not None:
            if str(parent) not in id_set:
                errors.append(f"parent_id 悬空: {sid} -> {parent}")
        title = str(raw.get("canonical_title", "")).strip()
        if not title:
            errors.append(f"canonical_title 为空: {sid}")
        policy_raw = raw.get("title_policy")
        try:
            TitlePolicy(str(policy_raw))
        except ValueError:
            errors.append(f"title_policy 未登记: {sid} -> {policy_raw!r}")
        required = bool(raw.get("required", True))
        conditional = str(raw.get("conditional_rule", "always"))
        if required and conditional != "always":
            errors.append(f"required 节点 conditional_rule 非 always: {sid}")

    # parent 成环检测
    parent_map = {
        str(r.get("section_id", "")): (None if r.get("parent_id") is None else str(r.get("parent_id")))
        for r in raw_sections
        if r.get("section_id")
    }
    for sid in id_set:
        seen: set[str] = set()
        cur = sid
        while cur in parent_map:
            if cur in seen:
                errors.append(f"parent 成环: {sid}")
                break
            seen.add(cur)
            parent = parent_map[cur]
            if parent is None:
                break
            cur = parent

    # order 重复（同 parent）
    order_seen: dict[tuple[str | None, int], str] = {}
    for raw in raw_sections:
        sid = str(raw.get("section_id", ""))
        parent = None if raw.get("parent_id") is None else str(raw.get("parent_id"))
        order = int(raw.get("order", 0))
        key = (parent, order)
        if key in order_seen:
            errors.append(
                f"order 重复: {order_seen[key]} 与 {sid} 同 parent={parent!r} order={order}"
            )
        order_seen[key] = sid

    return errors


def _build_template_spec(raw: dict) -> TemplateSpec:
    sections: list[SectionSpec] = []
    for sraw in raw.get("sections", []):
        canonical_title = str(sraw.get("canonical_title", ""))
        semantic_purpose = str(sraw.get("semantic_purpose", ""))
        purpose_code = derive_purpose_code(canonical_title, semantic_purpose)
        sections.append(
            SectionSpec(
                section_id=str(sraw["section_id"]),
                parent_id=None if sraw.get("parent_id") is None else str(sraw["parent_id"]),
                level=int(sraw.get("level", 1)),
                order=int(sraw.get("order", 0)),
                canonical_title=canonical_title,
                semantic_purpose=semantic_purpose,
                purpose_code=purpose_code,
                required=bool(sraw.get("required", True)),
                conditional_rule=str(sraw.get("conditional_rule", "always")),
                title_policy=TitlePolicy(str(sraw.get("title_policy", "fixed"))),
                allowed_aliases=tuple(sraw.get("allowed_aliases", []) or []),
                allowed_candidates=tuple(sraw.get("allowed_candidates", []) or []),
                max_length=int(sraw.get("max_length", 64)),
                dynamic_child_limit=int(sraw.get("dynamic_child_limit", 0)),
                allowed_child_purpose_codes=tuple(
                    PurposeCode(str(c)) for c in (sraw.get("allowed_child_purpose_codes", []) or [])
                ),
            )
        )
    return TemplateSpec(
        schema_version=str(raw.get("schema_version", "1.0")),
        title_spec_version=str(raw.get("title_spec_version", "1.0")),
        template_version=str(raw["template_version"]),
        module_key=str(raw["module_key"]),
        artifact_role=ArtifactRole(str(raw["artifact_role"])),
        sections=tuple(sections),
    )


def _find_file(
    template_dir: Path, module_key: str, artifact_role: ArtifactRole
) -> Path | None:
    matches: list[Path] = []
    for path in _iter_template_files(template_dir):
        try:
            data = _read_raw(path)
        except TitlePlanError:
            continue
        if str(data.get("module_key")) == module_key and str(data.get("artifact_role")) == artifact_role.value:
            matches.append(path)
    return matches[0] if len(matches) == 1 else None


def load_template(
    *,
    module_key: str,
    artifact_role: ArtifactRole,
    template_version: str | None = None,
    template_dir: Path | None = None,
) -> TemplateSnapshot:
    """加载唯一模板并返回不可变快照。

    找不到 → TEMPLATE_NOT_FOUND；多个候选 → TEMPLATE_AMBIGUOUS；
    内容非法 → TEMPLATE_CONTENT_INVALID；版本不匹配 → TEMPLATE_VERSION_MISMATCH。
    """
    directory = template_dir or DEFAULT_TEMPLATE_DIR

    # 唯一性：扫描 metadata，而非猜文件名
    candidates: list[Path] = []
    for path in _iter_template_files(directory):
        try:
            data = _read_raw(path)
        except TitlePlanError:
            continue
        if str(data.get("module_key")) != module_key:
            continue
        if str(data.get("artifact_role")) != artifact_role.value:
            continue
        candidates.append(path)

    if not candidates:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_NOT_FOUND,
            f"未找到模板: module_key={module_key} artifact_role={artifact_role.value}",
        )
    if len(candidates) > 1:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_AMBIGUOUS,
            f"模板不唯一: module_key={module_key} artifact_role={artifact_role.value}",
        )

    raw = _read_raw(candidates[0])
    declared_version = str(raw.get("template_version", ""))
    if declared_version in {"", "N/A", "OUT_OF_SCOPE"}:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_VERSION_MISMATCH,
            f"模板未就绪（template_version={declared_version!r}）: {candidates[0].name}",
        )
    if template_version is not None and declared_version != template_version:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_VERSION_MISMATCH,
            f"请求 template_version={template_version!r} 与模板 {declared_version!r} 不一致",
        )

    lint_errors = _lint_sections(list(raw.get("sections", [])))
    if lint_errors:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_CONTENT_INVALID,
            f"模板内容 lint 失败: {candidates[0].name}",
            detail={"errors": lint_errors},
        )

    template = _build_template_spec(raw)
    template_hash = stable_hash(canonical_json(template.model_dump(mode="json")), prefix="template:")
    return TemplateSnapshot(
        template=template,
        template_hash=template_hash,
        loaded_version=declared_version,
    )


def list_available_templates(template_dir: Path | None = None) -> list[dict]:
    """列出可加载模板（排除未就绪/未登记 role）。供 sync lint 与测试使用。"""
    directory = template_dir or DEFAULT_TEMPLATE_DIR
    result: list[dict] = []
    for path in _iter_template_files(directory):
        try:
            data = _read_raw(path)
        except TitlePlanError:
            continue
        role_raw = str(data.get("artifact_role", ""))
        try:
            role = ArtifactRole(role_raw)
        except ValueError:
            continue
        version = str(data.get("template_version", ""))
        ready = version not in {"", "N/A", "OUT_OF_SCOPE"}
        result.append(
            {
                "path": str(path),
                "module_key": str(data.get("module_key", "")),
                "artifact_role": role.value,
                "template_version": version,
                "ready": ready,
            }
        )
    return result


__all__ = [
    "DEFAULT_TEMPLATE_DIR",
    "list_available_templates",
    "load_template",
]
