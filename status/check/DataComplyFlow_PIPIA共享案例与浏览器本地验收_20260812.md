# DataComplyFlow PIPIA 共享案例与浏览器本地验收

> 日期：2026-08-12
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：PIPIA 三条共享正式场景；本地 HTTP、上传、异步任务、SSE、报告、PDF 预览和引用跳转
> 环境：本机 `127.0.0.1`，未连接远程服务器，未执行远程部署

## 结论

PIPIA 的共享案例迁移、后端结构化规则、前端可逆映射、真实本地 HTTP、异步状态、SSE 执行流、报告正文、PDF canvas 预览、引用跳转和产物登记已通过。PIPIA 仍保持“实施中”，因为本方案之外的其他模块浏览器验收和生产模型报告质量门禁尚未全部完成。

本次还修正了验收脚本的一个真实漏洞：后端任务 API 已完成时，前端自身的 1.5 秒轮询可能尚未将 `result.output_files` 写入 store，旧脚本会抢跑截图并产生“生成结果 0”。现在测试强制等待前端生成结果数量、报告风险、正文章节，以及 PDF canvas 完成渲染（`aria-busy=false`）。

## 逐案例证据

| 案例 | 来源分类与正式案例 | 统一事实 | 预期风险/状态 | CLI 断言 | HTTP 任务 | SSE | 截图 |
|---|---|---|---|---:|---|---:|---|
| `haitao_marketing_singapore` | `source_derived`；任务3测试案例一：跨境电商平台会员营销数据出境 | `benchmarks/cases/pipia/haitao_marketing_singapore/scenario.json`；SHA-256 `26f760e52d8e71219b5549ea751d805583fad07574870aa9f715ae6abceb9b5` | `MEDIUM / blocked`；标准合同缺失、告知/敏感分类/同意证据不足 | 33 | `813ab67dbeed4c6793919e6eae4a5f5d` | 1 | `haitao_execution_flow.png`、`haitao_report.png`、`haitao_pdf.png` |
| `weilan_hr_exemption_us` | `source_derived`；任务3测试案例二：跨国企业员工数据跨境人力资源管理 | `benchmarks/cases/pipia/weilan_hr_exemption_us/scenario.json`；SHA-256 `f325a88e128402c1e16bf291f82fa2c65884e5e4690dc9b2c11c92abd05feca4` | `MEDIUM / supplement_required`；HR 制度、员工手册、集体合同和接收方政策待核验 | 30 | `8e6aace167fd4851a99ec13382b1f20e` | 1 | `weilan_execution_flow.png`、`weilan_report.png`、`weilan_pdf.png` |
| `zhifutong_eurocert_de` | `source_derived`；任务3测试案例三：金融科技公司向境外认证机构传输数据 | `benchmarks/cases/pipia/zhifutong_eurocert_de/scenario.json`；SHA-256 `6e4813551ecc174c2fbdfac65ce2bc8efee62190cd49206dbd1929563782405b` | `HIGH / blocked`；认证机构资质、合法性基础和德国法/柏林管辖存在阻断风险 | 30 | `5c1bafc7cfc54703b618f92f3bb02734` | 1 | `eurocert_execution_flow.png`、`eurocert_report.png`、`eurocert_pdf.png` |

三份正式预期文件 SHA-256：

- `haitao.../expected.json`: `e6cacee944c28ef6ced2d16fb2539dd4be4bbfd76e5f2435711dbd35e5e67a7b`
- `weilan.../expected.json`: `1b67de21f2fd5496e828f5d5f5ae88caa5710a63fcc84b91c1f8349e276ee317`
- `zhifutong.../expected.json`: `1fe368f6f3533ba3358188eb5a7258f76e15bae1b678a388fc07b9a0247c7339`

附件哈希：

- 标准合同来源文档：`resources/new/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务3：“认证标准合同路径”路径描述及测试案例/“认证_标准合同路径”测试案例及预期输出.docx`；SHA-256 `3f2d7dd0dd842a7e15b17dbb8490517a4c4f71756057c7299f9e22c0e7aeec74`
- HR fixture：`backend/tests/pipia/fixtures/weilan_employee_handbook_excerpt.txt`；SHA-256 `70adddd86a8e3460d3291fcaff1802f775732d8bd409054ccffe1ff6c3aac50c`
- 认证 fixture：`backend/tests/pipia/fixtures/zhifutong_eurocert_contract_excerpt.txt`；SHA-256 `cf7ef3de9e298f8e0561d16d812894b73aa99c90fbc3c5412fdbad8e47edcc37`

## 请求语义门禁

浏览器提交前端最终请求后，测试同时校验：

- 业务字段与共享 `scenario.request` 完全相等（忽略上传后端路径）；
- 附件数量相等；
- `file_role`、`file_format` 相等；
- 上传生成的 `f_<hash>_` 文件名后缀仍必须等于共享案例原始文件名；
- `storage_uri` 的 basename 必须等于提交的 `file_name`；
- 风险、备案准备度、四条/三条结构化问题标题和五类产物角色均符合 `expected.json`。

相关实现和测试：

- `frontend/src/features/module-runner/payload-builders/cn.ts`
- `frontend/src/features/module-runner/model.ts`
- `frontend/tests/e2e/pipia-shared-cases-local.e2e.ts`
- `backend/domains/cn/pipia/schema.py`
- `backend/domains/cn/pipia/service.py`

## 本地验证结果

```text
PIPIA backend + CLI + parity pytest: 45 passed
Frontend full Vitest: 153 passed, 2 skipped
Frontend production build: passed
Case parity + semantic gate: 11 modules, 26 CLI cases, 603 leaf checks, 28 developer cases, passed
PIPIA shared browser HTTP/SSE/semantic suite: 3 passed (约 28s)
PIPIA full browser suite including citation jump and PDF canvas: 4 passed (45.5s)
```

浏览器证据目录：`status/check/phase3_pipia_shared_local/`。首次运行引用跳转证据仍在 `status/check/phase3_pipia_firstrun_20260808/browser/`。

证据安全边界：脱敏网络日志只保存 API path 和状态码。Playwright 原始 trace 会包含本地测试用户的 Authorization 请求头，配置已将后续 trace 和 HTML 报告移至 `tmp/verify/pipia-playwright/`，仅失败时保留，不得将原始 trace 作为 `status/check/` 证据提交；`.gitignore` 已增加 `**/playwright-results/`，防止历史 trace 被误提交。

浏览器专用服务使用 `backend/tests/pipia_browser_app.py` 中的确定性 LLM，仅用于稳定验证 HTTP、任务、Trace、报告回写和引用 UI，不代表生产模型文案质量。生产模型内容仍需独立的真实模型报告质量门禁。

## PDF 视觉验收

三条案例均满足：

- 后端返回 `pdf` 产物角色；
- 前端受权文件请求成功；
- `PdfViewer` 使用 `pdfjs-dist` 解析授权 Blob，并在 canvas 中渲染第一页；
- 测试等待 `aria-busy=false` 后检查 canvas 非白像素数大于 1000；
- `haitao_pdf.png`、`weilan_pdf.png`、`eurocert_pdf.png` 均显示中文标题、基础信息、风险等级、章节正文和分页控件；
- PDF worker、CMap 和标准字体资源由锁定依赖在本地构建时复制，未依赖远程资源；
- 页面无 PDF 请求错误。

文件级复核证明 PDF 产物本身并非空文件：三份均为 2 页 A4，文件大小约 4.9–5.1 KB，`pdftotext` 能提取企业、路径、接收方、风险和七章正文。使用本机 `pdftoppm` 渲染的第一页证据为：

- `haitao_pdf_rendered_page1.png`
- `weilan_pdf_rendered_page1.png`
- `eurocert_pdf_rendered_page1.png`

这些第一页可以正常显示。需要单独说明：浏览器专用服务使用 `backend/tests/pipia_browser_app.py` 的确定性 LLM，章节文本用于稳定验证输入、引用和渲染链路，不能代表生产模型的专业内容、重复率或最终报告质量；生产模型内容质量仍须使用真实模型和独立的内容质量门禁验收。

实现文件：`frontend/src/components/common/PdfViewer.tsx`、`frontend/src/components/common/pdf-document.ts`、`frontend/tests/e2e/pipia-shared-cases-local.e2e.ts`。PDF.js 依赖为 `pdfjs-dist@5.4.624`，通过 `npm run prepare:pdfjs` 准备本地 CMap 和标准字体资源。
