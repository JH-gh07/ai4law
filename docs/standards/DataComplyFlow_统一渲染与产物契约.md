# DataComplyFlow 统一渲染与产物契约

本文定义当前 12 个业务模块共享的报告结构、渲染入口和产物兼容边界。它描述已经落地并有测试的行为，不把历史设计稿中的候选抽象当成运行事实。

## 1. 分层与复用边界

报告链路按“业务数据 → 规范化 Markdown 或结构化 IR → 格式渲染器 → 模块结果字典/ReportService → Artifact API”分层。

| 层 | 当前入口 | 职责 |
|---|---|---|
| 业务模块 | `backend/domains/{cn,eu,us}/` | 形成事实、结论、引用和模块专属输出，不复制通用渲染引擎 |
| 结构化 IR | `backend/common/render/report_model.py` | 用 `ReportDocument`、`Section`、标题、段落、列表、表格、分隔线和引用表达报告 |
| Markdown 适配 | `backend/common/render/content_adapter.py` | 把 Markdown 拆成结构化块，禁止整篇文本塞入单一段落 |
| 格式渲染 | `backend/common/render/{markdown,html,docx,pdf}_renderer.py` | 从同一内容语义生成目标格式 |
| 既有简洁入口 | `backend/common/render/artifacts.py` | 保留稳定的 PDF、XLSX 和 ZIP 公共函数 |
| 持久化报告 | `backend/services/report_service.py` | 维护 owner、路径、预览、数据库记录和下载契约 |
| 前端预览 | `frontend/src/components/common/PdfViewer.tsx` | 通过鉴权 Artifact API 获取 Blob，负责加载、错误、重试和 URL 清理 |

`config/module_registry.json` 是模块身份的唯一权威源。渲染层不得再维护第二份模块表；没有生产消费者的 ArtifactRegistry 或 RenderProfile 不进入运行链路。

## 2. 结构化报告契约

`ReportDocument` 至少能够表达：报告元数据、章节、章节内标题、段落、有序/无序列表、表格、分隔线和引用。`ReportBuilder` 必须先建立 section 才能写 block，调用顺序错误直接抛出异常，禁止静默丢内容。

Markdown 输入先执行共享规范化契约，再由 `content_adapter` 分块。规范化的可执行事实源是测试：

- 后端读取 `backend/common/render/normalization_test_cases.json`；
- 前端直接读取同一 JSON，执行 `normalizeFallbackMarkdown`；
- 两端当前 14 个 Golden Cases 必须逐字一致；
- `normalization_rules.json` 只解释规则，不宣称自己是运行时 SSOT。

## 3. 格式行为

| 格式 | 最低保证 |
|---|---|
| Markdown | 标题、列表、表格、分隔线和引用结构不退化 |
| HTML | 保持块结构；所有不可信文本必须转义，不允许从报告正文注入脚本 |
| DOCX | 可被 `python-docx` 重新打开；标题、列表和表格仍可识别 |
| PDF | 文件以 `%PDF` 开头且可被 `pypdf` 打开；中文、标题、列表和表格有确定性渲染 |
| XLSX | 保留既有生成入口和模块输出键，不因 PDF 接入被替换 |
| ZIP | 只打包真实存在的文件；加入 PDF 时不得覆盖或删减原成员 |

`PdfRenderer` 是 ReportLab 实现上的窄入口，支持 Markdown、章节列表和模板三种调用。底层失败必须显式暴露或走已有的确定性降级，不允许只返回一个不存在的路径。

## 4. 模块输出兼容矩阵

所有模块均可生成有效 PDF；迁移只增加或复用能力，不删除原有输出。

| module ID | 必须保留的主要输出 |
|---|---|
| `cn.transfer_diagnosis` | HTML、PDF、结构化诊断结果 |
| `cn.security_assessment` | Markdown、DOCX、PDF、JSON、XLSX、ZIP、trace、CitationMap |
| `cn.document_review` | DOCX、annotated DOCX、JSON、PDF |
| `cn.pipia` | Markdown、DOCX、PDF、ZIP、CitationMap |
| `eu.scc_review` | Markdown、DOCX、annotated DOCX、findings、PDF、CitationMap |
| `eu.bcr_review` | 表单路径与文档路径各自的 Markdown、DOCX、PDF、ZIP |
| `eu.dpia` | Markdown、DOCX、PDF、JSON、XLSX、风险矩阵、整改计划、ZIP、trace、CitationMap |
| `eu.tia` | Markdown、DOCX、PDF、ZIP、CitationMap |
| `us.eo_14117` | Markdown、DOCX、PDF、XLSX、JSON、ZIP |
| `us.eo_14117_flow_review` | Markdown、DOCX、PDF、XLSX、JSON、ZIP |
| `us.cpra` | Markdown、DOCX、PDF、XLSX、JSON、ZIP、CitationMap |

## 5. 前端 PDF 契约

- PDF 与正文只按完全相同的文件 basename 配对，禁止回退到其他报告或其他批次；
- 同一组件挂载中的同一路径只发起一次 Blob 请求；
- retry 必须真正增加一次请求，不能只改变状态文案；
- path 变化和组件卸载都必须 `URL.revokeObjectURL`；
- 没有精确 PDF 伴随产物时，PDF tab 和下载按钮禁用；
- 加载、失败和重试使用可访问的状态与按钮语义。

## 6. 变更门禁

修改渲染链路至少运行公共 render 测试、涉及模块测试、前端 Golden Cases、前端组件测试和生产构建。新增格式前先证明有真实消费者；共享抽象不得以删除模块原输出或改变结果字典键为代价。
