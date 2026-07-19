# DataComplyFlow 法规知识资源

`resources/legal/` 是生产法规知识的唯一资源根目录。法规实体按法域只保存一份，模块适用关系由 catalog 和 registry 表达。

```text
legal/
├── catalog/
│   ├── sources.csv                 # 当前生产来源事实与有效快照路径
│   ├── practice_cases.csv          # 实务案例目录
│   ├── module_catalog.v1.json      # 模块、索引与启用策略
│   └── spec_asset_manifest.csv     # 历史资产迁移及可见性台账
├── registry/
│   ├── source_registry.v1.json     # 运行时活动来源注册表
│   ├── regulation_articles.jsonl   # 由 sources.csv 与快照构建的条款语料
│   └── regulation_article.schema.json
└── sources/
    ├── cn/{references,snapshots}/
    ├── eu/{references,snapshots}/
    └── us/{references,snapshots}/
```

## 权威关系

- `sources.csv` 保存来源事实和当前快照路径；
- `source_registry.v1.json` 是运行时注册表，source ID 必须与 `sources.csv` 一致；
- `regulation_articles.jsonl` 使用 `scripts/build_regulation_articles.py` 从当前来源重建；
- `module_catalog.v1.json` 表达模块与索引策略，不复制法规文件；
- `sources/` 中的 reference 是来源附件，snapshot 是可读取的法规文本或规范化摘录；
- 报告模板位于 `resources/templates/`，规则位于 `resources/rules/`；
- 模块说明与历史测试案例位于 `resources/research/module-specs/`，不得进入生产 RAG。

新增或更新法规时，必须同步 source ID、法域、版本状态、来源 URL、快照路径和有效日期，并重新构建条款语料及检索索引。