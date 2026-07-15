# Archived project material

Files under this directory are retained for historical traceability. They are
not current product entrypoints, runtime configuration, authoritative prompts,
or implementation facts. Consult `docs/engineering/` and `docs/handoff/` for
the current boundaries.

Archived material must not be imported by active code. If an archived asset is
needed again, restore it through a reviewed change with tests instead of adding
new runtime dependencies on this directory.

## 主要归档组

- `governance/`：已被后续实施记录或分阶段计划替代的治理方案和早期报告；
- `superpowers/`：基于 2026-06 目录及路由结构形成的设计和实施计划；
- `history/doc-error/`：历史故障分析与当时测试记录；
- `legacy/`：已退出活动路径的 Prompt、Schema 或实现资产；
- `plans/`、`verification/`、`architecture/`、`knowledge/`：早期项目规划和验证快照。

归档不代表内容错误，只表示它不再约束当前实现。任何恢复动作必须先与 `docs/engineering/`、当前代码和测试核对。
