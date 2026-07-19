# DataComplyFlow DOC-ROOT 第二批剩余资产收敛清单

## 1. 执行目标

本批只处理第一批迁移后仍位于 `doc/` 的 130 个文件，使仓库最终只保留 `docs/` 作为人类文档根目录。法域模块物理迁移、RAG v2/v3 合并、业务逻辑修复和法律 Gold 不在本批范围内。

## 2. 回退基线

- 备份：`.repo-backups/DataComplyFlow_pre_doc_root_phase2_20260716.zip`
- 大小：42,741,627 bytes
- SHA-256：`D58EA7E382A3762260CAA2149B36378568E88014AC94CDDEFAD38298AD3B0A7D`
- 备份内容：执行前完整 `doc/`，共 130 个文件。

## 3. 事实分类与处置

| 资产 | 数量 | 事实认定 | 处置 |
|---|---:|---|---|
| 原始产品资料中的法规、模板副本 | 65 | SHA-256 与 `resources/legal/` 或现有研究资产一致 | 删除重复副本，不再迁移 |
| 原始产品测试与功能说明 DOCX | 23 | 仓库内无相同 Hash，可能转化为 Benchmark 来源材料 | 按 `cn/eu/us` 迁入 `benchmarks/source-materials/` |
| 根目录测试输入 DOCX | 1 | 唯一测试来源材料 | 迁入 `benchmarks/source-materials/shared/` |
| `doc/开发文档/` | 18 | 无运行消费者，内容为历史流程、RAG、UI 设计记录 | 迁入 `docs/archive/legacy-development-notes/` |
| 根目录历史系统说明 Markdown | 10 | 非当前权威文档，Hash 唯一，仍有追溯价值 | 迁入 `docs/archive/legacy-system-notes/` |
| `doc/tmp/` 设计依据 | 12 | 不参与运行，但 34 处源码注释引用其设计章节 | 迁入 `docs/archive/legacy-design-specs/` 并更新注释路径 |
| 空 `motivation.md` | 1 | 0 字节，且与现有空文件重复 | 删除 |

## 4. 路径原则

- `docs/`：人类可读的现行文档和历史归档；
- `resources/`：运行时法规、模板和研究支撑资产；
- `benchmarks/`：评测数据、原始案例和待标注材料；
- `doc/`：本批完成后必须不存在；
- 历史 `origin_path` 可作为来源追溯字段保留，但不得再被活动代码当作可读取路径。

## 5. 验收门禁

1. 23 个法域来源材料和 1 个共享测试材料迁移前后 Hash 不变；
2. 65 个删除项均至少存在一个相同 Hash 的仓库副本；
3. 源码中的 `doc/tmp` 和前端中的原产品路径引用全部更新；
4. `doc/` 不再存在；
5. 后端测试、前端测试和生产构建通过；
6. 仓库卫生检查与 `git diff --check` 通过。


## 6. 执行结果

第二批已完成：

- 真实基线为 130 个文件；早期 118 的统计遗漏了 `doc/` 根目录 12 个文件，现已纠正；
- 65 个有相同 Hash 权威副本的法规或模板文件已删除；
- 24 个唯一 Benchmark 来源材料已按 `cn/eu/us/shared` 迁入 `benchmarks/source-materials/`；
- 40 个唯一历史设计与系统说明已迁入 `docs/archive/` 的三个 legacy 分组；
- 1 个空 Markdown 已删除；
- `doc/` 根目录已完全移除；
- 27 个后端文件中的历史设计注释已切换到 `docs/archive/legacy-design-specs/`；
- 前端开发案例附件已切换到 `resources/legal/` 中相同 Hash 的权威副本；
- 卫生检查现禁止重新提交任何顶层 `doc/` 路径。

Hash 复核结果：备份包含 130 个文件；当前仓库可找到全部 130 个内容 Hash；迁移后的 64 个唯一文件全部可回溯到备份；无缺失或意外内容。

验证结果：后端六组共 376 passed；前端 5 passed；前端生产构建成功；仓库卫生检查与 `git diff --check` 通过。前端错误边界测试输出的 `chunk load failed` 是测试主动构造的预期异常，测试退出码为 0。