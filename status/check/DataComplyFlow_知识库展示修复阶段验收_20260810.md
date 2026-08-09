# DataComplyFlow 知识库展示修复阶段验收（2026-08-10）

## 结论

本阶段只完成了知识库展示链路的第一批本地修复，不能宣称“索引和前端展示全部修复完成”。已完成的是：来源文本清洗增强、法规阅读页 Markdown 渲染、清洗回归测试和前端构建验证。

## 已落实

| 项目 | 代码位置 | 结果 | 证据 |
|---|---|---|---|
| 来源文本清洗 | `backend/services/knowledge_index.py:_clean_source_text` | 已增加 BOM/零宽字符、换行、HTML、HTML entity、欧盟公报页眉/页码、省略号噪音、中文硬换行和英文断字处理 | 后端单测通过 |
| 法规条文展示 | `frontend/src/pages/LawViewerPage.tsx` | 前后条文和当前条文统一使用 `ReactMarkdown + remarkGfm` 渲染，保留定位跳转 | 前端 TypeScript 构建通过 |
| 展示样式 | `frontend/src/styles/app/pages.css` | Markdown 段落、列表、引用块保留间距和换行，长文本自动换行 | 构建产物生成成功 |
| 清洗回归 | `backend/services/tests/test_knowledge_index.py` | 增加快照噪音清理、中文合并、英文断字和 HTML entity 用例 | `8 passed, 1 warning` |
| 前端回归 | `frontend/src/lib/fallback-markdown.test.ts` | 现有 Markdown 兼容测试通过 | `15 passed` |
| 前端构建 | `frontend/` | 生产构建通过 | `npm run build` |

## 尚未完成

| 项目 | 当前事实 | 不能提前宣称的内容 |
|---|---|---|
| 15 个索引内容质量 | 当前 JSONL 文件仍需逐模块核验来源覆盖、噪音比例和 module 分配 | 不能仅凭文件存在就宣称 RAG 全部可用 |
| 索引重建 | 本阶段没有重新生成 `storage/rag/v3/*.jsonl` | 不能宣称 P0-1 至 P0-4 已全部解决 |
| 7 个 metadata-only 来源 | 尚未完成来源清单治理和重建 | 不能宣称 metadata-only 已清零 |
| 浏览器展示 | 尚未启动本地前后端并使用 Playwright 截图 | 尚无页面视觉验收证据 |
| 引用跳转 | 代码路径保留，但尚未完成每个法域的真实点击闭环 | 不能宣称引用跳转全部正常 |
| PDF 页眉/页码 | 清洗函数已覆盖常见文本模式，尚未对全部来源重新抽样统计 | 目标“0 个问题文件”尚未证明 |

## 方案状态更正

`status/todo/DataComplyFlow_知识库索引修复方案_20260810.md` 文件头同时出现“v1.1 已完成”和“待执行”，状态自相矛盾。当前应按以下口径理解：

```text
索引修复方案：待完成全量重建、RAG 命中回归和引用利用率验收。
前端展示方案：第一批代码修复已完成，浏览器视觉验收和全量来源质量统计仍待完成。
```

## 本地验证命令

```bash
PYTHONUTF8=1 PYTHONNOUSERSITE=1 uv run pytest backend/services/tests/test_knowledge_index.py -q
cd frontend && npm test -- --run src/lib/fallback-markdown.test.ts
cd frontend && npm run build
```

## 变更边界

本阶段未连接远程服务器，未部署，未重建运行时产物，也未修改用户已有的其他未提交文件。
