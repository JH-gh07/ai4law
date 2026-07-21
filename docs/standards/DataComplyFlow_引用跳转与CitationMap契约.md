# DataComplyFlow 引用跳转与 CitationMap 契约

本文定义当前 CitationMap 的写入、读取和前端跳转边界。历史文件中的旧目录、固定行号和缓存 URL 结论均不作为现行事实。

## 1. 全链路

```text
domain report generation
  -> CitationRegistry / module grounding
  -> write_citation_map_json
  -> normalize_citation_item
  -> outputs/.../citation_map.json
  -> /api/v1/citations/reports/{task_id}
  -> normalize_citation_item（读取时再次规范化）
  -> CitationMarkdownRenderer / CitationArticleDrawer
  -> /knowledge/laws/{source_id}?article={article_no}
```

模块可以生成自己的 citation 数据结构，但写入标准 `citation_map.json` 时必须经过 `backend/common/citation/output.py` 的公共函数。安全评估和 DPIA 的模块包装函数也只委托公共 writer，不得直接序列化 `CitationItem.to_dict()` 绕过规范化。

## 2. 写入契约

`write_citation_map_json` 对 `footnote_map` 和 `all_items` 中的每一项调用 `normalize_citation_item`。公共任务管理器在模块尚未写 CitationMap 时可以从 payload 合成，但合成结果同样必须经过公共 writer。

规范化至少保证：

- 尽可能把标题或历史 source 值解析为知识库的规范 `source_id`；
- 中文条号和“第 X 条”转换为稳定的阿拉伯数字；
- `knowledge_url` 每次由规范 source 与定位字段重新生成，不信任旧运行产物中的缓存值；
- `module`、`jurisdiction`、`display_label`、`anchor`、`section_id`、`clause_id`、`open_mode`、`can_jump` 和 `source_url` 具有稳定字段；
- 相同输入重复规范化保持幂等。

## 3. URL 字段语义

| 字段 | 含义 | 约束 |
|---|---|---|
| `knowledge_url` | 站内法条阅读器地址 | 由 `build_knowledge_url` 生成，不接收磁盘中的陈旧缓存作为权威值 |
| `source_url` / `external_url` | 法规外部官方来源 | 不得冒充站内阅读器地址 |
| `source_id` | 知识库稳定来源 ID | 能解析时使用规范 ID；不能解析时保留原值并由 `can_jump` 表达能力 |
| `article_no` | 条款定位 | 写入 URL 前统一规范数字形式 |
| `anchor` / `section_id` / `clause_id` | 非条号定位 | `article_no` 缺失时按公共函数优先级选择一种定位参数 |

标准站内地址形式为 `/knowledge/laws/{source_id}`，可带 `article`、`section`、`clause` 或 `anchor` 查询参数。source ID 和查询参数必须由 URL 编码逻辑处理，不在模块中手工拼接。

## 4. API 读取契约

Citation API 位于 `backend/api/v1/endpoints/citations.py`，支持报告 CitationMap、批量条目和单条详情。API 从模块输出目录读取或恢复 CitationMap 后，在响应组装阶段再次调用公共规范化函数；这样旧运行产物中的空 URL 或错误 URL 不会直接泄漏给前端。

找不到 CitationMap 时返回空集合，而不是伪造引用。恢复路径生成了新 CitationMap 时，仍使用公共 writer 落盘。

## 5. 前端消费契约

`CitationMarkdownRenderer` 获取报告的 `footnote_map`，将正文引用标记关联到引用详情；`CitationArticleDrawer` 展示详情并提供内部法条入口。前端允许根据 `source_id + article_no` 构造同语义的站内 fallback，以抵御旧缓存数据，但不得把外部 URL 当内部 URL。

跳转行为必须满足：

- 内部阅读跳转到 `/knowledge/laws/...`；
- 外部官方来源使用独立字段和明确入口；
- 无有效 source 时不显示可跳转状态；
- CitationMap 获取失败不阻断正文渲染。

## 6. 验证门禁

引用链路修改至少运行：

```bash
uv run --frozen pytest -q backend/common/citation/tests
uv run --frozen pytest -q backend/api/v1/tests/test_citations_api.py
```

默认 pytest 必须能发现 `test_citation_url_normalization.py`。测试覆盖条号转换、URL 构造、陈旧缓存重建、writer 双集合规范化、幂等性、domain 包装路径和前端消费所依赖的 API 响应契约。
