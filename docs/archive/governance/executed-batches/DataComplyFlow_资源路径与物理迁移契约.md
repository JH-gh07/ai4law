# DataComplyFlow 资源路径与物理迁移契约

## 目标

资源路径已完成第一轮物理收敛：报告模板按法域存放，活动法规迁入`resources/legal/`，评测数据迁入`benchmarks/datasets/product_smoke/` 与 `benchmarks/datasets/rag_retrieval/`。活动代码必须通过`backend/core/resource_paths.py`定位仓库资源，禁止继续新增`Path("doc/...")`硬编码。

## 当前兼容位置

| 资源 | 当前物理位置 | 代码入口 | 当前状态 |
|---|---|---|---|
| 法律知识库 | `resources/legal/` | `KNOWLEDGE_ROOT`、`knowledge_path()` | 已迁出历史`doc/` |
| 报告模板 | `resources/templates/{cn,eu,us}/` | `REPORT_TEMPLATE_ROOT`、`report_template_path()` | 已按法域迁移 |
| RAG评测数据 | `benchmarks/datasets/product_smoke/` 与 `benchmarks/datasets/rag_retrieval/` | `PRODUCT_SMOKE_BENCHMARK_ROOT` / `RAG_RETRIEVAL_BENCHMARK_ROOT` | 已与生产法规隔离 |
| 当前技术文档 | `docs/` | 人工阅读入口 | 权威文档目录 |
| 论文支撑材料 | `resources/research/papers/` | 无生产代码调用 | 已与生产资源分离 |
| 产品设计来源材料 | `resources/research/product-design-sources/` | 无生产代码调用 | 已与活动文档和生产资源分离 |

活动代码已不再定义`LEGACY_DOC_ROOT`，报告模板和法规知识源均不再依赖`doc/v2`或`doc/knowledge`。

## 已确认缺口

- `4.2_us_14117_compliance_template_v0.docx`不存在；当前服务会创建空DOCX作为降级输出，不能认定为完整DOCX交付能力；
- `2.3_pipia_template_v0.docx`与`.md`不存在；PIPIA服务通过存在性判断降级，需单独补齐合法来源模板或调整正式交付契约；
- 前端开发测试案例中的活动法规附件路径已切换到`resources/legal/...`；原始产品案例路径仍在后续`doc/`清理批次处理；
- 一次性脚本`scripts/migrate_knowledge_base.py`无活动消费者且迁移目标已完成，本批删除，历史实现由Git和阶段备份保留。

## 物理迁移门槛

从`doc/`迁移到`resources/`前必须满足：

1. 活动后端不再直接硬编码`doc/knowledge`或`doc/v2/assets/templates`；
2. 模板与知识路径专项测试通过；
3. 知识索引能够从注册表重建；
4. 前端开发案例和迁移脚本已有新路径适配；
5. 迁移前后文件Hash和数量清单一致；
6. 后端全量测试、RAG固定评测和报告生成Smoke通过；
7. 迁移与重复文件删除分为两个独立提交。

## 建议目标结构

```text
resources/
├── legal/
│   ├── cn/
│   ├── eu/
│   └── us/
├── templates/
│   ├── cn/
│   ├── eu/
│   └── us/
└── research/
```

法域共享法规原则上只保存一份源文件，各业务模块通过注册表和source ID引用，不再按模块复制同一PDF。

## 2026-07-15 模板迁移记录

- 迁移13个已跟踪模板到`resources/templates/cn`、`eu`和`us`；
- 迁移前后Git对象Hash逐项一致；
- 删除迁移后为空的`doc/v2/assets/templates`、`doc/v2/assets`和`doc/v2`目录；
- 未生成缺失的PIPIA和EO 14117 DOCX模板。

## 2026-07-15 研究材料迁移记录

- 原`paper/`的14个文件迁入`resources/research/papers/`；
- 原`doc/addition/`的28个文件迁入`resources/research/product-design-sources/`；
- 42个文件迁移前后Git对象Hash逐项一致；
- 研究材料不作为活动法规、Prompt、模板、Fixture或运行配置入口，使用边界见`resources/research/README.md`。
