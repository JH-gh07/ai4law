# task067 验收报告（BCR 三格式专业排版与统一 IR 渲染）

- 生成时间：2026-08-13
- 结论：**T00–T10 完成；T11 公共回归完成，BCR 旧正式路径退出被环境前置条件阻断（`BLOCKED_BY_TOOLING` + `BLOCKED_BY_FONT`）——task067 不能标记为「完成」。**
- 证据根目录：`status/check/task067/`

## 1. 一句话结论

四 renderer（Markdown / Web / DOCX / PDF）已经全部只读同一份 v4 `DocumentIR`，跨格式同源由 render manifest 的 hash + 等价门禁证明，排版回归门禁与三 viewport / DOCX / PDF 视觉证据齐全；但「把 BCR 用户产物正式切换到 IR renderer、并删除旧模板正式路径」这一收尾动作被本机缺失 LibreOffice 与可再分发 CJK 字体阻断，按方案 §十一「失败条件」第 7、8 条不得声称通过，故 task067 保持未完成、切换保持本地 opt-in。

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| T00 基线与工具冻结 | ✅ | LibreOffice 缺失、CJK 字体缺口已如实登记（见 `environment.json`） |
| T01 DocumentIR v4 排版契约 | ✅ | 12 类 block 联合 + `extra=forbid` + compiler fail-closed |
| T02 BCR 结构化 adapter | ✅ | `BCRFinding[]` 直出 v4 IR，编译门禁 fail-closed |
| T03 IR → Markdown | ✅ | 只读 IR，未知 block fatal |
| T04 受控 IR API + Web 阅读版式 | ✅ | `report_ir` API + `ReportDocumentView` |
| T05 IR → DOCX 原生 | ✅ | 原生表/Heading/多级编号/页眉页脚，ZIP 时间戳定版 |
| T06 IR → PDF 定版 | ✅ | `rl_config.invariant` 确定性，字体显式注册 |
| T07 render manifest + 等价证明 | ✅ | 原子写 manifest + hash/等价门禁 |
| T08 排版回归门禁 | ✅ | `layout_gate.py` + 变异测试 + CLI 脚本 |
| T09 影子渲染 + 本地切换 | ✅ | `shadow_render.py` + `bcr_report_ir_rendering_enabled` + 回滚验证 |
| T10 真实视觉验收 | ✅ | PDF 逐页栅格 + headless 三 viewport + DOCX 结构（视觉 `BLOCKED_BY_TOOLING`） |
| T11 公共回归 + 旧路径退出 | ⚠ 部分 | 回归全通过；**旧路径退出被环境阻断**（见 §4） |

## 3. 公共回归结果（T11 回归范围）

| 范围 | 结果 |
|---|---|
| 方案 §9.1 `reporting + render + bcr_review` | **176 passed** |
| 方案 §9.2 `artifact API + contracts + citation` | **206 passed** |
| 合并 `reporting+citation+contracts+BCR+artifacts` | **356 passed** |
| 后端全量 `pytest backend/` | **1132 passed / 3 failed**（3 例均为 `cn/pipia`×2、`eu/scc_review`×1，与 task067 无关） |
| 前端 report/css 组件 | **9 passed** |
| 前端全量 `npm test` | **187 passed / 2 failed**（`cn/pipia`、`cn/scc` 的 dev-case fixture，与 task067 无关） |
| 前端 `npm run build` | **通过**（修复 `use-report-ir.ts` 未使用 `module` 参数的 TS6133） |
| `git diff --check` | **通过**（顺带修复 `knowledge/ingestion_pipeline.py` 的 pre-existing 尾随空格） |
| 证据敏感内容扫描 | **无** token / `.env` / secret / password / 真实用户上传正文 |

## 4. 旧路径退出：BLOCKED 与解除条件

方案 §十 Checkpoint D 要求「LibreOffice 和字体门禁**真实通过**」后才能退出 BCR 旧正式路径。本机现状：

- `soffice`/`libreoffice` **缺失** → DOCX 视觉 `BLOCKED_BY_TOOLING`；
- 无可再分发 CJK 字体 → PDF 中文字体 `BLOCKED_BY_FONT`（拉丁 `LiberationSans emb=yes`，CJK 退化 `STSong-Light emb=no`）。

按 §十一 第 7、8 条，此时**不得**声称 PDF 可复现 / DOCX 视觉通过，因此**不执行**以下动作，避免违反环境约束：

- 不把 `bcr_report_ir_rendering_enabled` 默认改为 `true`；
- 不把 `schema_first_bcr_enabled` 默认改为 `true`；
- 不删除 BCR 正式路径对 `_build_markdown_table()` / `render_docx_template()` / `render_markdown_template()` / `from_template()` 的依赖；
- 不删除或改判旧模板（其他模块可能仍用公共 legacy 函数，§T11 禁止未覆盖前改动）。

当前实际可见路径（满足 §十一 第 13 条「新旧路径不同时对用户可见」）：

- 默认（双 flag 均 `false`）→ 仅旧模板路径对用户可见，IR 影子渲染到 `shadow_ir/`；
- 本地切到 IR（双 flag 均 `true`）→ 仅 IR renderer 路径对用户可见，旧模板停放到 `shadow_legacy/`。

**解除条件（缺一不可）：**

1. 引入已获授权并登记 hash 的可再分发 CJK 字体，使 `pdf_font_embedding` gate 由 `blocked` → `pass`；
2. 安装 LibreOffice headless，使 DOCX→PDF→PNG 视觉门禁由 `BLOCKED_BY_TOOLING` → `pass`；
3. 复查 Checkpoint D 全部条目后，将 `schema_first_bcr_enabled` 与 `bcr_report_ir_rendering_enabled` 默认置为 `true`，删除旧模板正式路径（保留 archive/reference + 迁移说明），并删除影子 flag 临时分支。

## 5. 排版结构证据（非「文件存在」弱断言）

`structural_checks.json`（18 finding 压力样本，`render_status=success`）：

```
compile                 pass
ir_hash_immutable       pass
required_artifacts      pass
equivalence             pass
pdf_font_embedding      blocked   ← 诚实阻断，不伪造
six_column_table ×3     pass
broken_fragments ×2     pass
markdown_residue ×2     pass
artifact_hash           pass
equivalence             pass
```

PDF 逐页栅格（`pdftoppm`）：controller 2 页 / high-risk-health 5 页 / 18-finding 7 页，三 layout 门禁全 pass。
headless 三 viewport（1440×900 / 1280×800 / 390×844）：9 张截图，`violations=[]`、`console_errors=[]`、无横向滚动、无重复正文。

## 6. 环境约束（未违反）

- 未远程连接、未部署；
- 未写入用户正文 / token / `.env` / secret（证据仅结构化 ID、hash、截图、结构统计）；
- DOCX 视觉 `BLOCKED_BY_TOOLING`、PDF CJK `BLOCKED_BY_FONT` 如实记录，未伪造 PASS。

## 7. 下一步

满足 §4 三条解除条件后，重开 task067 执行 T11 收尾：切默认 flag → 旧模板归档 → 删除影子 flag 分支 → 重新跑全量回归与 `git diff --check` → 更新本报告为「完成」。
