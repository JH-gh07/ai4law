"""L1 Platform shared model — Missing / Gap traceability (task081).

A MissingItem is the atomic record of *one* missing / gap observation at *one*
trace stage.  It answers four questions independently so the platform can stop
conflating them:

  1. Where did the gap first appear?            → ``stage``
  2. What kind of gap is it?                    → ``type``
  3. Where is the evidence for that attribution? → ``source_paths``
  4. Did the fact reach the model, and was it called? → presence flags + ``llm_called``

The root-cause label is derived from the whole chain, never asserted on a
no-llm run as a model error (``MODEL_OUTPUT`` is forbidden when
``llm_called`` is False).

This module is shared by every report module; no module should define its own
missing schema.
"""

from __future__ import annotations

import glob as _glob
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────

MissingType = Literal[
    "input",          # 输入/附件确实没有提供
    "rule",           # 规则引擎或 Issue Builder 判断缺失
    "evidence",       # 证据/材料不充分
    "legal_basis",    # 法律依据缺失
    "control",        # 控制措施未实施/未体现
    "assembly",       # 代码拼接时丢失字段/证据/章节上下文
    "prompt",         # 必需事实没有进入实际模型 Prompt
    "model_output",   # 事实已进 Prompt，模型输出仍不一致
    "render",         # 输出协议/Schema/Renderer 失败
    "test_contract",  # 代码行为与旧 Benchmark 期望不一致
]

MissingRootCause = Literal[
    "INPUT_MISSING",
    "RULE_MISSING",
    "ASSEMBLY_MISSING",
    "PROMPT_MISSING",
    "MODEL_OUTPUT",
    "RENDER_SCHEMA",
    "TEST_CONTRACT",
    "NOT_VERIFIED",
    "NOT_EXECUTED",
]

MissingStatus = Literal[
    "OBSERVED",      # 已观测到并归因
    "RESOLVED",      # 已修复/已消除
    "NOT_VERIFIED",  # 证据不足以归因
    "NOT_EXECUTED",  # 未执行或依赖不可用
]


# ── Core model ────────────────────────────────────────────────────────────

class MissingItem(BaseModel):
    """A single missing / gap observation at a single trace stage."""

    missing_id: str = Field(min_length=1, description="Unique missing record id")
    module: str = Field(min_length=1, description="Module key, e.g. 'assessment'")
    stage: str = Field(
        min_length=1,
        description="Trace stage where the gap first appeared, e.g. 'issues_built'",
    )
    type: MissingType = Field(description="Kind of gap")
    item_key: str = Field(
        min_length=1,
        description="Stable key of the affected item, e.g. 'ISSUE-missing-attachments'",
    )
    source_paths: list[str] = Field(
        default_factory=list,
        description="Trace / input / code evidence paths backing the attribution",
    )
    present_in_global_context: bool = Field(
        default=False,
        description="The field/fact exists in the global context pack",
    )
    present_in_model_prompt: bool = Field(
        default=False,
        description="The field/fact actually entered the model prompt",
    )
    present_in_model_output: bool = Field(
        default=False,
        description="The field/fact appears in the model output",
    )
    llm_called: bool = Field(
        default=False,
        description="Whether a real LLM call happened for this stage",
    )
    root_cause: MissingRootCause = Field(description="Root-cause label")
    status: MissingStatus = Field(default="OBSERVED", description="Attribution status")

    @field_validator("module", "stage", "item_key", "missing_id", mode="before")
    @classmethod
    def _strip_nonempty(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("required string field must be non-empty")
        return value


class MissingManifest(BaseModel):
    """Per-module, per-run collection of MissingItem records.

    ``module`` + ``run_id`` identify a single run.  The collection validator
    enforces the uniqueness contract: one record per (item_key, stage) and one
    unique missing_id per run.
    """

    schema_version: str = Field(default="1.0")
    module: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    no_llm: bool = Field(
        default=False,
        description="True when the run used a disabled LLM",
    )
    items: list[MissingItem] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


# ── Validation ────────────────────────────────────────────────────────────

def validate_missing_item(item: MissingItem) -> list[str]:
    """Return a list of validation errors for a single MissingItem.

    Empty list means the item is valid.  Rules:

    R1  required identity fields are non-empty (enforced by Pydantic too).
    R2  presence flags must be monotonic down the pipeline:
        output -> prompt -> global context.
    R3  no-llm runs must never be attributed MODEL_OUTPUT, and MODEL_OUTPUT
        requires a real LLM call with the fact present in the prompt.
    R4  OBSERVED / RESOLVED records must carry at least one evidence path;
        NOT_EXECUTED / NOT_VERIFIED may carry none.

    Note: ``present_in_global_context=true`` with ``present_in_model_prompt=false``
    remains *permissive* — a fact recording "this input is absent" (e.g. an empty
    uploaded_files fact) is legitimately present in the global context, so
    ASSEMBLY_MISSING / PROMPT_MISSING / INPUT_MISSING / NOT_VERIFIED are all
    accepted for that combination.  The schema must never reject the two causes
    the plan requires (ASSEMBLY_MISSING / PROMPT_MISSING).
    """
    errors: list[str] = []

    # R2 — presence flag monotonicity
    if item.present_in_model_output and not item.present_in_model_prompt:
        errors.append(
            f"{item.missing_id}: present_in_model_output=True requires "
            "present_in_model_prompt=True"
        )
    if item.present_in_model_prompt and not item.present_in_global_context:
        errors.append(
            f"{item.missing_id}: present_in_model_prompt=True requires "
            "present_in_global_context=True"
        )

    # R3 — no-llm / MODEL_OUTPUT attribution
    if item.root_cause == "MODEL_OUTPUT" and not item.llm_called:
        errors.append(
            f"{item.missing_id}: root_cause=MODEL_OUTPUT requires llm_called=True"
        )
    if item.llm_called and item.root_cause == "MODEL_OUTPUT" and not item.present_in_model_prompt:
        errors.append(
            f"{item.missing_id}: MODEL_OUTPUT requires the fact to have reached "
            "the prompt (present_in_model_prompt=True)"
        )

    # R4 — evidence path requirement
    if item.status in {"OBSERVED", "RESOLVED"} and not item.source_paths:
        errors.append(
            f"{item.missing_id}: status={item.status} requires at least one source_path"
        )
    if item.source_paths and any(not p or not p.strip() for p in item.source_paths):
        errors.append(f"{item.missing_id}: source_paths must not contain empty strings")

    return errors


# Concrete run ids look like ``20260818_082134_316356_02_healthdata_source_draft``:
# ``YYYYMMDD_HHMMSS_<micro/seq>_<case_id>``.  Synthetic aggregate ids such as
# ``task081-consolidated`` do not match, so manifests keyed by those ids skip the
# run-id consistency check below.
_CONCRETE_RUN_ID_RE = re.compile(r"\b\d{8}_\d{6}_\d+_\w[\w-]*\b")


def validate_missing_source_paths(
    item: MissingItem, base_dir: Path | str
) -> list[str]:
    """Validate that each ``source_path`` resolves to at least one real file.

    ``source_path`` entries are treated as repository-relative.  Glob patterns
    (``*``/``?``/``[``) are expanded and must match at least one *file*; plain
    paths must point to a file (``is_file()``).  Directory matches are rejected
    so a directory path cannot masquerade as a file evidence path.  Absolute
    plain paths are checked as-is.  Empty/blank entries are already rejected by
    R4 and are skipped here.
    """
    base = Path(base_dir)
    errors: list[str] = []

    for raw in item.source_paths:
        if not raw or not raw.strip():
            continue

        if _glob.has_magic(raw):
            pattern = raw if Path(raw).is_absolute() else str(base / raw)
            matches = [m for m in _glob.glob(pattern, recursive=True) if Path(m).is_file()]
        else:
            candidate = Path(raw) if Path(raw).is_absolute() else base / raw
            matches = [str(candidate)] if candidate.is_file() else []

        if not matches:
            errors.append(
                f"{item.missing_id}: source_path {raw!r} does not resolve "
                f"to any file under {base}"
            )

    return errors


def validate_missing_manifest(
    manifest: MissingManifest, *, base_dir: Path | str | None = None
) -> list[str]:
    """Validate the whole manifest.

    Always checks per-item semantic rules (R1-R4), uniqueness, and module
    attribution consistency (``item.module`` must equal ``manifest.module``).
    When ``base_dir`` is provided, additionally verifies that every
    ``source_path`` resolves to at least one real file (glob-aware), so that a
    "0 errors" result also means the evidence paths are actually usable.
    """
    errors: list[str] = []
    seen_missing_id: set[str] = set()
    seen_item_key_stage: set[tuple[str, str]] = set()

    for item in manifest.items:
        errors.extend(validate_missing_item(item))

        if item.module != manifest.module:
            errors.append(
                f"{item.missing_id}: item.module={item.module!r} does not match "
                f"manifest.module={manifest.module!r}"
            )

        # Run-id consistency: when the manifest is keyed by a concrete run id,
        # no source_path may embed a *different* concrete run id (stale-run guard).
        if _CONCRETE_RUN_ID_RE.fullmatch(manifest.run_id):
            for raw in item.source_paths:
                for rid in _CONCRETE_RUN_ID_RE.findall(raw):
                    if rid != manifest.run_id:
                        errors.append(
                            f"{item.missing_id}: source_path embeds run_id {rid!r} "
                            f"but manifest.run_id={manifest.run_id!r}"
                        )

        if base_dir is not None:
            errors.extend(validate_missing_source_paths(item, base_dir))

        if item.missing_id in seen_missing_id:
            errors.append(f"duplicate missing_id: {item.missing_id}")
        seen_missing_id.add(item.missing_id)

        key = (item.item_key, item.stage)
        if key in seen_item_key_stage:
            errors.append(
                f"duplicate (item_key, stage): {item.item_key!r} @ {item.stage!r}"
            )
        seen_item_key_stage.add(key)

    return errors


__all__ = [
    "MissingItem",
    "MissingManifest",
    "MissingRootCause",
    "MissingStatus",
    "MissingType",
    "validate_missing_item",
    "validate_missing_manifest",
    "validate_missing_source_paths",
]
