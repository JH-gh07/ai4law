# DataComplyFlow RESOURCES-AUTHORITY 资源权威源治理契约

> 状态：completed
> 执行日期：2026-07-17
> 范围：`resources/legal/`、`resources/rules/`、`resources/templates/`、`resources/research/` 及其路径消费者。

## 1. 目标与非目标

本批按“正确 → 简洁 → 补强”建立资源单一事实来源：法规实体按法域只保留一份，模块适用关系由 catalog/registry 表达，研究材料与生产法律资源分离。

本批不修改法规正文、规则阈值、模板内容、RAG 切分算法、检索排序或法律 Gold；不因来源可疑直接删除唯一文件。

## 2. 修改前基线

- `resources/` 共 522 个文件，约 247 MB，整个目录尚未纳入当前 Git 索引；
- `legal/` 463 个文件，约 158 MB；`research/` 43 个文件，约 89 MB；
- SHA-256 扫描得到 148 组重复内容、293 个重复实例，理论重复占用约 107.4 MB；
- 模块目录与 `raw/` 中共有 433 个 reference/snapshot 文件，按“法域 + 类型 + SHA-256”仅有 167 个唯一实体；
- `sources.csv` 和活动 `source_registry.v1.json` 均为 93 条且 source ID 集合一致；
- `source_registry.v1.generated.json` 仅 19 条，无运行消费者；
- 运行时通过 `backend/common/knowledge/paths.py` 读取 catalog/registry，通过 `resources/rules/` 和 `resources/templates/` 读取规则及模板；
- 前端开发案例有 4 个模块目录硬编码路径，需要随迁移同步。

## 3. 目标结构

```text
resources/
├── legal/
│   ├── catalog/                 # 来源、案例、模块关系与资产清单
│   ├── registry/                # 活动 source registry、条款 JSONL 与 schema
│   └── sources/
│       ├── cn/{references,snapshots}/
│       ├── eu/{references,snapshots}/
│       └── us/{references,snapshots}/
├── rules/{jurisdiction}/        # 运行时确定性规则
├── templates/{jurisdiction}/    # 审核后的运行时报告模板
└── research/
    ├── papers/
    ├── product-design-sources/
    └── module-specs/{jurisdiction}/{module}/
```

## 4. 执行规则

1. reference/snapshot 按“法域 + 类型 + SHA-256”去重；
2. 每组优先保留 `raw/` 文件名，否则采用最短稳定模块路径中的文件名；
3. 复制到新路径后重新计算 SHA-256，验证一致才删除旧副本；
4. 同步更新 `sources.csv`、活动 registry、条款 JSONL、spec manifest 和前端开发案例中的路径；
5. 模块 `spec.md` 与 `test-cases.md` 移至 research，不进入生产法律资源；
6. 删除无消费者的旧生成注册表和一次性迁移摘要；
7. 保留所有唯一内容以及来源台账，不对法律内容作主观取舍。

## 5. 验收门禁

- 93 条 source snapshot 路径全部存在；
- spec manifest 的 target path 全部存在；
- 活动 registry 与 sources.csv 的 source ID 集合一致；
- `regulation_articles.jsonl` 中所有 snapshot 路径存在；
- 前端构建、知识注册表测试、知识索引测试、RAG 检索测试通过；
- 仓库卫生检查与 `git diff --check` 通过；
- 迁移前后 167 个唯一资源 SHA-256 集合保持不变。

## 6. 回退条件

任一唯一资源 Hash 缺失、路径消费者未更新或知识/RAG 测试失败时，停止删除并恢复相应旧路径。性能优化、法律版本校订和来源许可确认另行处理。
## 7. 实际执行结果

- 433 个旧 module/raw 文件收敛为 167 个法域权威文件；
- 删除 266 个 SHA-256 完全相同副本，167 个唯一 Hash 全部保持；
- `legal/` 从 463 个文件、约 158 MB 收敛为 151 个文件、约 51.40 MB；
- 20 个模块 spec/test 文件迁入 `research/module-specs/`；
- `source_registry.v1.generated.json` 与 `migration_summary.json` 作为无消费者中间物删除；
- 21 条历史 spec/test manifest 记录改为 `tracked_only`，67 条生产资产保持 `frontend_visible`；
- 修复旧条款 JSONL 的 629 条失效 `doc/v3` 快照路径；退役非法律的功能说明、测试案例和清单后，从 69 个当前来源重建为 1672 条、0 失效路径；
- 24 个非法律 source ID 无消费者且内容已转存研究区，已从生产来源退役；
- 69 个 source、69 个 registry entry、69 个 JSONL source 的身份集合一致；
- 剩余 8 组跨 `legal/` 与 `research/product-design-sources/` 的相同文件为来源证明副本，按生产权威版与设计来源版的不同职责保留，不再形成模块级重复。

验证结果：资源/知识/RAG 测试 51 项通过；前端测试 6 项通过；TypeScript 与 Vite 生产构建通过。构建的大 chunk 提示属于既存性能事项，不影响本批资源正确性。
