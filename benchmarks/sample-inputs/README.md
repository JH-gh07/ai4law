# Benchmark sample inputs

本目录过去保存合成输入样本供前端开发预设使用。

**自 2026-08-07 起**，测试输入 fixture 已迁移至 `backend/tests/fixtures/{cn,eu,us}/`，
按法域组织存放，便于跨前后端共享与自动化测试发现。

旧占位文件（`sample_contract.txt`、`sample_evidence.txt`、`data_inventory.csv`、
`entity_inventory.csv`）已删除，对应引用已更新至 `backend/tests/fixtures/` 或 `resources/legal/`。

## 目录结构

```
backend/tests/fixtures/
├── cn/
│   ├── data_security_agreement.docx   # 数据安全协议（document_review 模块）
│   ├── cn_flow_data_inventory.csv     # 数据清单（cn_flow 模块）
│   └── cn_flow_entity_inventory.csv   # 实体清单（cn_flow 模块）
├── eu/
│   ├── scc_2021_en.md                 # SCC 2021 标准合同条款（eu_scc 模块）
│   └── bcr_c_globaltech.docx          # BCR 主文档含审查缺陷（bcr 模块）
└── us/
    ├── us14117_data_inventory.csv     # 数据清单（us_14117 模块）
    └── us14117_entity_inventory.csv   # 实体清单（us_14117 模块）
```

## 原则

- 样本不得包含真实客户、员工、源代码、凭据或未经确认的法律 Gold 结论。
- 运行时上传副本写入被 Git 忽略的 `storage/uploads/`。
