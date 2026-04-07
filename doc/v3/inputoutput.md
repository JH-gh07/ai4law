下面按**当前 PIPIA 流程的“小阶段”**拆解，每一段都写清楚**输入 → 输出**（和关键承载对象）。

---

**1. 入口请求构造（API/本地调用）**  
**输入**：`PIPIARequest`  
- `company_profile`（企业名称、行业、出境人数等）  
- `transfer_context`（目的、接收方、国家、合法性基础）  
- `personal_info_scope`（数据类型、人数）  
- `rights_protection` / `emergency_plan`  
- `attachments`  

**输出**：内存中的 `PIPIARequest` 实例  
- 用于后续所有流程  
- 定义：`backend/modules/pipia/schema.py`

---

**2. 法条检索（RAG）**  
**输入**：检索 query（由业务信息拼接）  
- 例如：`PIPIA standard contract certification + 目的 + 接收国`  
- 传入：`retrieve_regulations(... jurisdiction="cn", path="scc")`

**输出**：`list[RegulationDoc]`  
- 结构：`title / article / content / source`  
- 用途：  
  - 构造 `citations`（法规标题+条款）  
  - 构造 `reg_snippet`（上下文片段）  
- 代码：`backend/common/rag/retriever.py`

---

**3. 上下文组装（Context Block）**  
**输入**：  
- `PIPIARequest`（企业/业务/规模）  
- `risk_level`（规则算出的）  
- `reg_snippet`（检索结果）

**输出**：`context_block: str`  
- 模板化文本（企业信息 + 法规参考）  
- 给 LLM 生成章节用  
- 代码：`backend/modules/pipia/service.py`

---

**4. 章节生成（LLM）**  
**输入**：  
- `context_block`  
- `chapter_title`  
- `SYSTEM_PROMPT + CHAPTER_INSTRUCTIONS + STRICT_CONSTRAINT`

**输出**：`chapter.content`  
- 每章一段正文  
- 已强制补引用链（后处理）  
- 代码：  
  - `backend/common/llm/module_generator.py`  
  - `backend/common/llm/postprocess.py`

---

**5. 章节集合（结构化输出）**  
**输入**：每个章节的 `content` + `citations` + `risk_level`  
**输出**：`list[PIPIAChapter]`  
- 结构字段：`chapter_no / title / content / citations / risk_level`  
- 代码：`backend/modules/pipia/schema.py`

---

**6. 一致性与输入对齐检查**  
**输入**：  
- `PIPIARequest`  
- `chapters`  

**输出**：`issues: list[str]`  
- 例如：  
  - “scc_filing 但未上传合同”  
  - “内容出现欧盟，但接收国是 Singapore”  
- 代码：  
  - `backend/modules/pipia/service.py::_check_consistency()`  
  - `backend/common/quality/alignment.py`

---

**7. 模板映射与摘要化**  
**输入**：  
- `chapters`（长文本）  
- `citations`（法规列表）  
- 模板字段列表（如 `necessity_analysis`）

**输出**：`mapping: dict[str, str]`  
- 每个字段是“摘要 + 依据尾注”  
- 代码：  
  - `backend/common/render/summary.py`  
  - `backend/modules/pipia/service.py::_build_template_mapping()`

---

**8. 模板渲染输出（最终文件）**  
**输入**：  
- `mapping`  
- Markdown 模板文件 `doc/v2/assets/templates/2.3_pipia_template_v0.md`

**输出**：  
- `outputs/pipia/TemplateTestCo_PIPIA_报告_草案_20260407.md`  
- 同时渲染 docx / zip

**代码**：  
- `backend/common/render/report.py::render_markdown_template()`  
- `backend/modules/pipia/service.py::_render()`

---

如果你需要，我可以把这份“阶段输入输出清单”直接写成文档放到 `doc/v3/优化.md`，作为开发文档。