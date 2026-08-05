# DataComplyFlow 功能预期与实际对照分析

> 审计日期：2026-08-06  
> 审计基线：`826e23d`（new 分支）  
> 文档性质：逐功能对比「设计预期」与「代码实际表现」  
> 事实优先级：可运行代码与实测命令 > 自动化测试 > 历史文档 > 规划描述  
> 证据来源：  
> - 2026-08-05 浏览器全功能运行验证截图  
> - pytest 528 passed / vitest 48 passed  
> - CLI 15/15 PASS（no-LLM模式）  
> - 前端 26 案例直投真实 API（9/26 成功）  
> - 后端代码审计（700+ `.py` 文件）  
> - 前端代码审计（3,751 行 ModuleRunPanel + 1,412 行 dev-test-cases）

---

## 一、模块注册与任务入口

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 模块数量 | 系统有 12 个完整可用的业务模块，按中/欧/美三法域划分，每个模块都是独立的完整功能实体 | 实际 `module_registry.json` 注册了 **11 个模块**（`cn.scc_review` 已退役为 legacy-compatible）；前端展示 11 个任务入口 |
| 模块注册唯一权威源 | 所有模块信息（ID、法域、路由、生命周期）应在单一注册表中定义，前后端和 CLI 均从此读取 | `config/module_registry.json` 是权威源，但前端 endpoint、表单、模板散落在 `api/modules.ts`、`task-templates.ts`、`module-adapter.ts` 多处独立编码 |
| `us.eo_14117_flow_review` 模块定位 | 应是中国数据流转检查（CN Flow），检查中国企业数据出境的流转合规性 | 前端 key 为 `cn_flow`，但 system prompt（`module_generator.py:55-60`）写的是 **"美国 EO 14117 合规律师"**，实际生成面向美国法域；API 前缀 `/api/v1/cn-flow` 暗示中国功能，功能语义严重混乱 |
| `cn.scc_review` 模块 | 应为可选的中国标准合同审查模块，可独立运行 | 已标记为 `legacy-compatible`，前端任务模板中**未单列**；后端路由仍注册，但其 `generate_report()` 曾因 `uuid is not defined` 断链 |
| 前端任务模板覆盖 | 10 类任务模板应覆盖全部 11 个模块，并提供明确的任务创建与执行入口 | 10 个模板覆盖 `diagnosis`/`assessment`/`review`/`pipia`/`cn_flow`/`eu_scc`/`bcr`/`dpia`/`tia`/`us_14117`/`cpra`，**等于 11 个**，但 `cn_flow` 和 `us_14117` 的语义交叉导致用户选择困惑 |
| "一键体验"功能 | 对 11 个模块，前端应均可通过预设案例一键填充表单并触发真实后端运行 | 2026-08-05 浏览器实测：**仅 4/11 成功产出**（diagnosis、assessment、pipia、cpra）；其余 7 个中 BCR/DPIA/TIA 在前端 `buildPayloadFrom()` 阶段即因 `"Invalid or missing required input"` 失败，未到达后端 |

---

## 二、运行执行与任务编排

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 统一工作流管道 | 所有模块共用 `WorkflowPipeline`，实现一致的 profile→facts→issues→evidence→context_pack→chapters→consistency→repair→render 流程 | 公共 `WorkflowPipeline` 仅在 **assessment、EO 14117、CN Flow** 三个模块使用；其余 8 个模块（SCC、PIPIA、BCR、DPIA、EU SCC、TIA、CPRA、review）各有**独立专用 service**，不通过公共 pipeline |
| CN Flow 与 Pipeline 参数契约 | `build_context_pack()` 应接受 pipeline 传入的 `per_issue_rag` 参数，形成完整的检索上下文 | `CNFlowService._build_context_pack()` 的签名与 `WorkflowPipeline.run()` 传入的 `per_issue_rag` 不兼容，**service 和 v0 测试直接失败**（见 `backend/domains/us/eo14117_flow_review/service.py:166`） |
| 异步任务提交 | 异步生成端点返回 task/trace id，前端通过 SSE 或轮询获取进度和结果 | 异步 API `/generate_async` 在 BCR、CPRA、DPIA、PIPIA、TIA 等模块存在，但本轮测试中这些端点**要求鉴权**而测试未携带 auth header，返回 401；**不是业务逻辑失败，而是测试契约与实际接口不一致** |
| v0 网关统一映射 | v0 gateway 将旧版请求映射到当前 11 个模块，保持向后兼容 | v0 DPIA 返回 **400**（payload 映射与当前 schema 不匹配）；v0 gateway 支持模块集合不完整，不含 diagnosis、SCC、EU SCC、EO 14117 |
| 任务持久化 | 任务状态应落盘或在数据库中持久化，服务重启后可恢复并查看历史运行 | 除 `document_review` 使用 SQLite 任务表外，其他模块的任务状态**仅在内存**（`InMemoryTaskManager`），**进程重启即丢失运行状态**；最小 `run_manifest.json` 已落盘但前端历史页尚未接入 |
| 任务取消 | 取消操作应真正终止后台线程/LLM 调用，并释放资源 | `cancel` 只改变内存状态标记，**不终止已运行的线程**；已发起的 LLM 调用继续执行到完成 |

---

## 三、中间过程、Token 与执行流

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 执行事件时间线 | 每次运行产生有序的 start/progress/end 事件，前端实时展示节点名称、耗时和状态 | 2026-08-05 安全评估浏览器真实验证：**事件 0、节点 0**，左侧已出现 22 项生成结果但右侧执行流**完全空白** |
| Token 统计 | 每次 LLM 调用记录 input/output/total token，前端展示模块 Token 和总 Token 数字 | 同一安全评估运行：**模块 Token `--`、总 Token `--`**，完全为空；CLI `--no-llm` 模式下 Token 正确显示为 0 |
| 运行耗时 | 前端展示从提交到完成的 wall-clock 时间，单位为 ms 或 s | 前端 `TraceRunHeader.tsx:55-85` 有耗时计算代码（`durationMs`），但同一运行显示**"用时 --"**；后端 `run_manifest.json` 有 `duration_ms` 字段但前端未读取 |
| 中间产物展示 | 前端应以结构化视图展示 Fact/Issue/Evidence/ContextPack 的生成进度，而非仅文件列表 | 诊断模块和其他模块的"中间产物"标签均显示**"当前模块尚未生成该中间产物"**；后端实际生成了这些 JSON/XLSX，前端以原始文件列表形式呈现 |
| SSE 事件持久化 | 事件应增量写入持久存储，SSE 只是传输通道；服务重启后可从存储恢复完整时间线 | SSE 事件**仅在内存**，任务结束后 **30 分钟自动清理**；服务重启即丢失；`run_manifest.json` 只有事件计数无事件详情 |
| run_manifest 完整性 | 每次运行产生统一 run_manifest，包含 run_id、task_id、user_id、状态、总 Token/耗时、ProviderSnapshot、输入输出摘要 | 已落盘最小版本，但**不包含** CitationMap 统计、RAG/得理调用明细、案例 ID 归属、usage source（provider_reported vs estimated）；前端历史页未接入 |
| 成本统计 | 按运行汇总 Token 并乘以单价得到成本，可用于预算门禁 | **无统一价格表和成本计算**；Token 只代表供应商返回或估算量，不等于可核账费用 |

---

## 四、引用体系（Citation）

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 引用—正文绑定 | 报告中每句法律结论应有对应脚注，脚注号码与 CitationMap 一一对应，点击可跳转到具体法条原文 | 2026-08-05 安全评估 citation_map.json 有 **7 条引用**，但正文写**"本报告未引用法规依据索引"**；正文提到《个人信息保护法》《数据安全法》却标注**"待核验：缺少法规依据"**；引用映射与报告正文**完全断链** |
| 精确跳转（can_jump） | 只有来源和条号在本地知识库唯一匹配时才能精确跳转；其他情况应进入来源概览或显示失败原因 | 7 条引用中仅 **1 条 `can_jump=true`**（14.3%）；其余 6 条因 `article_not_found` 或 `article_not_unique` 不可跳；缺失条号的引用曾经仅因"source_id 非空"就被标为可跳，**已修复**（P0-04） |
| 知识库重复定位键处理 | 各法规来源应消歧，确保每个 (source, article) 组合在知识库中唯一可解析 | 知识库有 **34 组重复定位键**；这些键已被降级为不可精确跳转（`source_overview`），但最终消歧仍需法律内容负责人确认 |
| CitationResolution 解析类型 | 应区分 `exact_article`、`source_overview`、`external_verified`、`unresolved` 四种解析类型，前端根据不同状态显示不同交互 | 已引入 CitationResolution 体系（已修复），但前端交互尚未完全区分四种类型，抽屉对所有情况显示基本相同的界面 |
| 外部引用（得理案例）与本地引用隔离 | 得理返回的案例 ID 不得写入本地 source_id 字段；外部引用应标记为 `external_verified` 并走独立解析管线 | 历史数据中**1 个得理案例 ID 不在知识库却被标记 `can_jump=true`**；3,126 个已知来源引用**没有条号**，只能定位到来源级别 |
| source_url 跳转 | 引用应包含法规官方来源 URL，用户可从抽屉点击跳转官方原文 | 安全评估 citation_map.json 的 7 条引用中 **source_url 均为空**；知识库中 1,273 行条文标记为 `reference` 状态，**无 source_url** |
| 引用在报告正文中的交互 | 用户点击正文中的引用角标，弹出法规条文原文抽屉，支持复制引用、查看前后条文 | 引用脚注在正文中**完全缺失**；引用映射以原始 JSON 独立标签呈现；**无"复制引用"按钮**、无法规新规标签 |
| 证据与主张的关系 | 每条引用应有 `support_relation`（direct_support/partial_support/background/conflict/insufficient），并追溯对应的 Claim ID 和 Evidence Span | **无统一的 ClaimItem 类**，无法将最终报告拆成 claim 并逐 claim 校验；support_relation 和 evidence span 体系**未实现** |
| 报告内部标记泄露 | 内部 ISSUE 编号、待核验标记、禁用措辞移除标记等不应在客户交付报告中可见 | 安全评估 Markdown 中出现 **`ISSUE-...`**、**`【待核验】`**、**`【已移除禁用措辞...】`** 外露，严重不适合作为客户交付稿 |

---

## 五、法规知识库与 RAG 检索

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| RAG 哈希向量确定性 | 同一查询在不同进程/重启后应产生完全相同的检索结果 | Python `hash()` 已替换为 **SHA-256 固定映射**（P0-06 已修复）；索引记录版本号，不兼容索引自动重建 |
| 中国法规精确召回 | 查询"个人信息保护法第三十九条"应在首条命中该法条原文 | 2026-08-05 实测：首条命中**模板**（非法律原文），第2、3条才命中个保法第39条和第29条；模板排在法律前的排序策略不理想 |
| EU 法规精确召回 | 查询"GDPR Article 35 DPIA"应首条命中 GDPR 第35条原文 | 实测返回 3 个 EU supporting 文档段落，**未直接命中 GDPR 第35条**；EU 精确条款召回不达预期 |
| 中文离题拦截 | 查询"今天天气怎么样"且 jurisdiction=cn 时应返回空结果或提示无相关法规 | 实测**仍然返回 DPA/安全评估办法等法规**；中文离题查询的拦截失败 |
| 本地 RAG + 远程得理混合 | 本地结果不足时自动补充远程法规，远程结果经来源对齐后入库 | 得理真实探测失败（`PROVIDER_ERROR`），本轮**未真实用通**；本地 RAG 结果不足时直接回落空结果或启发式结果 |
| 法规有效版本过滤 | 检索应过滤已失效版本，仅返回当前有效法规 | 版本与有效期 metadata 存在于 `SourceRegistryEntry.is_current_version/status`，但**检索阶段没有统一的"仅当前有效版本"强制过滤** |
| 使用策略隔离 | L3 testcase 不得进入 production external report；L4 template 仅限法律证据和内部用途 | `UsagePolicyFilter` 存在并可限制不同层级材料进入最终报告，但**仅在公共 pipeline 中使用**，各独立模块不统一调用 |
| 法规条文到知识库覆盖率 | 170 个原始知识文件应全部高质量解析为条件/例外级原子规则 | 有 article_split 和章/节/条/款/项层次标记，但**并非所有 170 个文档都证明已高质量解析**；不能认定为完整"条件/例外级法律检索" |

---

## 六、LLM 调用与 Agent 体系

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| CN Flow system prompt 法域正确性 | CN Flow 模块的 system prompt 应定位于**中国数据流转合规**，关注《数据安全法》《个人信息保护法》等中国法规 | system prompt（`module_generator.py:55-60`）写的是**"美国 EO 14117 合规律师"**，与模块语义完全矛盾；可能在评估时造成法域污染 |
| LLM Provider 健康探测 | 保存 provider 配置前应自动探测模型可用性；不可用时明确阻断并显示错误类型（模型不存在/余额不足/鉴权失败等） | 健康探测已实现（ENV-BLOCK-01 已部分关闭），能区分模型不存在、下线、余额不足、鉴权失败；但当前**默认腾讯混元模型不可用**，生产门禁会阻断——属于**外部环境阻断** |
| Agent 自治能力 | 应是真正的 Agent 体系，具备多轮规划、工具调用、动态决策能力 | 所有"Agent"实质是**单次 LLM JSON 调用 + 规则 fallback**；无 ReAct 循环、工具规划、长期记忆或多 Agent 协商；更准确称呼为"Agent 命名的结构化 LLM 专家步骤" |
| CN Flow 诊断 Agent | 诊断模块的 Agent（ImportantDataAgent、PIClassifyAgent）应辅助但不覆盖确定性规则 | Agent 在**规则命中前**可将 unknown 改为 yes/no，从而**改变输入事实**；规则命中后的解释 Agent 才受"不得改判"约束；因此"AI 永不影响确定性结果"只在确定性命中后成立 |
| 修复失败阻断 | `REPAIR_BLOCKED` 标记应阻止 renderer 输出，防止不合格报告自动交付 | Pipeline 中标记 `REPAIR_BLOCKED` 后**仍然调用 renderer 输出文件**；`repair_blocked` 仅向 `consistency_issues` 添加文本，"修复失败自动阻断交付"与代码行为不一致 |
| LLM 降级说明 | 模型不可用时的降级报告应在**顶部醒目标识**，而非仅在末尾出现 | 降级说明仅在报告末尾出现，且报告前文中段的风险等级（HIGH/MEDIUM）自相矛盾，未因降级而统一降级 |

---

## 七、规则引擎

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 统一规则引擎 | 全平台应有统一的规则引擎，规则有版本号、有效期、生效日期和冲突检测 | **多套机制并存**：JSON 决策表、Python if-else 函数、rulebook JSON + loader、静态 riskbook 等；普遍**无版本管理、无 effective date gating、无规则冲突求解** |
| 中国路径规则顺序 | 豁免规则应正确排序，CIIO/重要数据判断在豁免之前执行，确保不会在未确认关键风险时提前豁免 | 豁免规则中的 `q1_is_ciio` 和 `q2_has_important_data` 可接受 **`unknown`**，且豁免规则**排在强制评估规则之前**；可能在 CIIO/重要数据未确认时给出豁免（代码事实和风险） |
| 规则 vs AI 冲突策略 | 应有平台级"规则优先于 AI"的强制策略，规则结果为最终结论 | 不存在统一策略；中国 diagnosis 在确定性命中后不允许 AI 改判，但命中前 AI 可修改 unknown；EO 14117 `rule_boundary` 返回 overrides；BCR Agent 可新增 finding 和改评级 |
| 未命中解释 | 当无规则匹配时应给出可解释的默认路径和理由，而非静默选择 | unknown 处理不是严格保守：`_normalize_answers()` 会依据表单材料**推断** q2/q5 和人数；当信息不足时形成显式 AI 推测路径 |
| 规则版本快照 | 每次运行的规则版本应可重放，确保审计可追溯 | 规则作为代码/JSON 常量存储，**无运行时的规则版本快照**；代码更新后历史规则不可精确重放 |

---

## 八、报告生成与渲染

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 风险等级一致性 | 同一报告中 overall risk、中段评估结论和最终结论的风险等级应完全一致 | 安全评估 Markdown 实测：前文 **overall risk HIGH**，中段写**"综合风险等级 MEDIUM"**，后文又 **HIGH**；同一报告自相矛盾 |
| 表格渲染 | Markdown 表格应在预览中正常显示为表格形式 | 实测出现 **"项目内容/企业名称/数据处理目的..." 连成纯文本**，Markdown 表格语法未正确渲染 |
| 换行与格式 | TLS 1.3 等固定格式应保持完整，不被拆分 | 实测 **`TLS 1.3` 被拆为 `TLS` + 空行 + `3`**；文本清洗/自动换行破坏固定格式 |
| 内部标记隔离 | 报告正文中不应出现系统内部标记 | 实测出现 `ISSUE-...` 编号、`【待核验】`、`【已移除禁用措辞...】` 外露 |
| 标题层级 | Markdown 应有清晰的层级结构，便于扫描 | 多个章节更像是纯文本段落，**层级扫描性弱** |
| 占位内容处理 | "该部分内容待补充"不应作为完整交付段进入正式正文，应进入待办附录或显式标注 | 占位内容直接进入交付正文 |
| 免责声明 | 按 PRD 要求，报告应有三处固定位置的完整免责声明和水印 | 有"仅供参考"但**未完全匹配 PRD 固定文案和三处展示**要求 |
| 多格式一致性 | 同一报告的 MD/DOCX/PDF 在结构、表格、引用上应一致 | `resources/templates/cn/` 存在 v0 模板与官方自评估模板的**结构不一致**（7节 vs 三大章），双源并存 |
| 降级模式 vs 正常模式 | 降级报告应明确标识为降级版本，与正常 LLM 生成报告有清晰区分 | 降级只在末尾提一句，报告中段仍呈现高级结论，没有**全篇降级标识** |

---

## 九、输入输出文件管理

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 产物归属 | 每个产物文件应绑定到具体 run_id/user_id，预览和下载需要所有权校验 | P0-01 已修复（删除路径回退授权）；但历史未登记产物无法验证归属 |
| 文件展示 | 前端以用户可理解名称展示（如"安全自评估报告（PDF）"），按角色分组（输入/过程/报告/数据附件） | 文件以**原始文件名（含日期后缀、内部编号）**展示；同路径可按不同 kind 重复登记 |
| 物理路径泄露 | 不应在 API 和前端契约中暴露服务器物理路径 | 历史存在路径泄露；ArtifactRecord/ContentBlob 模型已定义但**未全量迁移** |
| 运行输出冗余 | 应有明确的产物保留策略，区分调试文件与交付产物；ZIP 内不应重复保存已在外层目录存在的文件 | `outputs/` 目录有 **42,022 个文件、约 1.1 GiB**；ZIP 包中内容与外层散件双重存储；Python 缓存 **7,723 个 .pyc 文件** |
| 思诚资料重复 | 入库前应按 SHA-256 去重，避免重复索引 | 三组 ZIP 包解压后发现 **8 组相同内容哈希**；多个 `.html` 与 `.md` 内容相同仅扩展名不同 |

---

## 十、测试案例体系

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 前后端案例统一 | 前后端应基于同一套权威案例集，案例 ID 一致，payload 可互换 | 前端 26 个案例 vs 后端 CLI 15 个案例，**不是同一套**；前端案例的 `payload` 声称"可直接 POST"但 **17/26 失败** |
| 案例 Schema 同步性 | 案例 payload 应随后端 Schema 更新同步维护，保持字段、枚举值一致 | diagnosis 案例中 `q6_scenario=business_operation`、`q7_receiver_type=affiliated_company` **不在当前枚举**中；PIPIA 案例缺少 `company_uscc` 等当前必填字段 |
| 案例强断言 | CLI 测试应对路径、风险等级、法条、章节做**强断言**，而非仅 `result_not_empty` | 多数 `expected` 只断言 **`result_not_empty`**，对路径正确性、风险判断、法条引用、模板章节缺少强 oracle |
| "一键体验"可靠性 | 11 个模块的"一键体验"应均可正常完成表单回填→payload 构建→提交运行 | 仅 **4/11 成功**；BCR/DPIA/TIA 的 `buildPayloadFrom()` 即抛出异常，未到达后端；EU SCC 和 US 14117 提交后报 Pydantic `Field required` |
| 测试覆盖完整性 | 应覆盖所有关键路径：成功场景、边界失败、Schema 校验、引用完整性、RAG 命中 | 后端 **528 passed, 0 failed**（全部为离线测试）；前端 **48 passed, 0 failed**（全部为单元测试）；**无浏览器 E2E 测试** |

---

## 十一、外部服务集成（得理法搜 + LLM Provider）

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 得理法搜真实可用 | 设置页显示"已启用"时应可真实调用 API，返回法规和案例结果 | 2026-08-05 真实探测返回 **`PROVIDER_ERROR`**；Mock 测试通过但**真实调用失败** |
| 得理结果归一化 | 返回结果应保留稳定 ID、条号、效力状态、原文片段、官方 URL | 适配器当前仅保留 **title、source、summary** 三个字段；丢弃了 gid、条号、案号、生效状态、URL，无法支撑可信引用入库 |
| 得理条件触发 | 仅在本地置信度不足 / HIGH-BLOCKER issue / 用户要求最新法规时才调用，非默认并行检索 | 当前触发逻辑分散在各模块：安全评估对 HIGH/BLOCKER 额外搜索；文书审查对部分条款搜索；通用 RAG 在本地无结果时触发——**不是统一策略** |
| LLM Key 安全 | Key 不应回显、不进日志、不进运行产物，以脱敏指纹保存 | 设置 API 返回时隐藏 Key；`runtime_settings.json` 曾明文保存，需**严格文件权限**管理；ProviderSnapshot 对 Key 做 SHA-256 摘要，禁止 repr |
| Provider 健康检查与阻断 | 生产环境下如无健康 LLM，任务启动前应明确阻断，返回可理解的错误信息 | 生产门禁已实现（ENV-BLOCK-01），15 分钟内的有效探测结果 + Provider 指纹一致性校验；开发环境和 `--no-llm` 不受影响 |
| "小李 AI" Provider | 文档暗示可连接小李 AI，应有对应的 provider 配置入口和模型探测 | 代码中**无"小李 AI"具名提供商**；仅支持通用 OpenAI-compatible provider；需要在有 Base URL、模型名和鉴权方式后才能接入 |

---

## 十二、安全与权限隔离

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 产物跨用户隔离 | 用户 A 不能访问用户 B 的报告文件，通过 artifact ID、task ID 或路径猜测均被拒绝 | P0-01 已修复：删除基于路径字符串的授权回退，统一通过 `ReportArtifact`/`UploadedFile` 归属校验 |
| 事件流权限 | 获取任务事件需要验证当前用户是否为任务所有者 | P0-02 已修复：新增 `TaskOwnershipModel` 持久化，事件流、CitationMap、状态、重试均鉴权；非所有者返回 404 |
| 引用读取权限 | 读取 CitationMap 需要任务所有权验证 | P0-02 已修复，与事件流共用统一授权逻辑 |
| 运行时配置权限 | 修改全局 LLM/得理配置应需要管理员权限，避免任意用户影响全平台 | **任何已认证用户可修改全局提供商设置**，无管理员权限区分 |
| 密钥脱敏 | Provider 的 API Key 在存储、日志、API 响应中均不出现明文 | 设置 API 返回时隐藏；`runtime_settings.json` 明文存储需文件权限保护；ProviderSnapshot 的 `api_key` 被 SHA-256 摘要且禁止 repr |

---

## 十三、前端交互体验

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 引用角标点击行为 | 点击应为站内受控交互：打开法规条文抽屉，显示条文原文和前后条，可站内导航；官方外链在抽屉内以"查看官方来源"按钮提供 | 曾存在 `window.open(..., "_blank")` 直接新开页面（已修复）；当前为站内受控交互，但**四种 CitationResolution 类型的前端区分尚未完整** |
| Markdown 表格滚动 | 宽表应有稳定横向滚动容器，移动端可滑动查看 | 宽表滚动容器**不完善**；部分模块表格显示为纯文本 |
| 文件预览/下载分组 | 产物按"输入材料/过程证据/最终报告/数据附件"分组显示；主报告默认打开；不支持的格式明确"仅可下载" | 文件以 `ResourcePanel` 原始列表呈现，**未按 role 分组**；图片、XLSX、ZIP 等预览在不同模块表现不一致 |
| 执行时间线 | 运行结束后应可回溯查看完整节点轨迹，包括每个节点的名称、耗时、输入输出 token | assessment 运行后"暂无执行记录"；**0 事件、0 节点**，但存在 22 件产物；事件桥接 `TaskEventBridge` 未将后端产出正确关联 |
| 模块专属"一键体验"按钮重复 | 应只有一套统一的"开发测试"入口，开发环境可见，生产不可见；不应有多个行为不一致的专用按钮 | 同时存在**通用案例选择器**和**多个模块专用一键按钮**，行为不一致；US 14117 和 CN Flow **无一键运行按钮**（P1 缺口） |
| 表单回填准确性 | 选择测试案例后，表单字段应完整回填，与后端 Schema 一致 | diagnosis 等模块通过 UI builder 可转换部分字段，部分枚举值映射丢失；BCR/DPIA/TIA 回填直接失败 |

---

## 十四、数据结构与一致性

| 功能点 | 预期合理现象与逻辑 | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 统一 Fact/Issue/Evidence | 所有模块共用公共 `FactItem`/`IssueItem`/`EvidenceItem`/`GenerationContextPack` schema，形成跨模块一致的事实—规则—证据链 | 公共 schema 存在，但 BCR、PIPIA、TIA、EU SCC、CPRA、review 多用**专用 Finding/Gap/DTO**，公共 IR 覆盖不统一 |
| ClaimItem 存在性 | 应有统一的 `ClaimItem` 类，将最终报告拆成独立 claim，支持逐 claim 的 evidence attribution 和 faithfulness 验证 | **不存在 ClaimItem 类**；SCC 中 `_extract_claims()` 使用普通 dict；EvidenceItem 的 claim 字段是生成前的证据陈述，不是最终文本 claim |
| RuleItem 存在性 | 应有统一 `RuleItem` schema，包含条件、例外、法律效果、优先级、版本、有效日期 | **不存在 RuleItem 类**；规则分布在 JSON 决策表、Python if-else、rulebook JSON、静态 riskbook 等多种格式中 |
| 数据库实体统一 | 所有模块任务应在统一的任务表中持久化，有统一的 `task_id`、`run_id` 和 `owner_id` | 只有 `document_review` 有独立 SQLite 任务表；其余模块任务在内存中，**无统一任务表** |
| trace manifest 双契约 | 只应有一个 trace manifest 契约，所有模块按同一格式写入 | 存在两个 trace 方向：`TraceRecorder` 的 manifest 和 `TraceManifest` 模型（workflow/trace.py），前者实际使用后者未采用 |
| ReportDocument 源头统一 | Markdown 输出应是单一语义源（ReportDocument）的渲染产物，不应多个模块各自直接生成 Markdown 字符串 | 只有部分模块使用 `ReportDocument` → renderer；多数模块**直接生成 Markdown 字符串**；前后端有两套不同的 Markdown 规范化逻辑 |

---

## 十五、模板与需求匹配（vs 思诚 PRD 2026-08-04 v0.1.0）

| 功能点 | 预期合理现象与逻辑（PRD 要求） | 当前实际问题现象与逻辑 |
|--------|-------------------|-----------------------|
| 每条结论绑定法条 | 报告中的每条法律结论必须绑定"法规名+条号+摘要"，错误率 0 | 正文无脚注，引用映射未串联；出现《网络安全法》第4条关联"敏感个人信息定性"等**可疑映射**，未达到可验收状态 |
| Word/PDF 水印 + 免责声明 | 固定水印和完整免责声明，报告中至少三处固定显示，不可移除 | 部分输出有简化免责声明，**未证明三处固定显示和不可移除** |
| 法条高亮/复制引用/新规标签 | 前端应在引用抽屉中提供法条原文高亮、一键复制引用按钮和新规标签 | 前端**未见完整控件** |
| 人工复核六类条件冻结 | 当满足六类复核条件（置信度低、高风险、涉及新规等）时自动冻结报告，等待人工复核后放行 | 当前主要是**提示**而非冻结队列；无统一审批状态机 |
| 置信度 < 90% 自动复核 | 置信度低于 90% 的结论应自动进入复核流程 | **未见统一实现** |
| WORM 日志 | 日志应满足 WORM（一次写入多次读取）要求，至少保留 3 年，记录操作 IP、规则版本、复核意见 | 当前 trace/数据库**不是 WORM 完整账本** |
| 100 个律师核验案例 | 应有 100 个经律师核验的案例，准确率 ≥ 95% | 当前 CLI 仅 15 个案例且 oracle 为弱断言；**不匹配** |
| 官方模板逐字对齐 | PIA/自评估/SCC/BCR/DPIA/TIA 应严格按官方模板逐字生成 | 当前 `resources/templates/eu` 只有 BCR、TIA 两份；assessment 存在 v0 模板与官方模板的双源冲突；CN 缺少 diagnosis/PIPIA/document review/EU SCC/DPIA 的权威模板 |

---

## 十六、跨模块一致性总览

| 维度 | 预期 | 实际 | 差距 |
|------|------|------|------|
| 工作流编排 | 统一 WorkflowPipeline | 仅 3/11 模块使用 | **8 个模块独立实装** |
| 结构化中间产物 | 统一 Fact/Issue/Evidence | 公共 schema 存在但非全模块 | **5+ 模块用专用类型** |
| 引用体系 | 统一 CitationRegistry + CitationMap | 存在但跨模块不统一 | diagnosis/review 独立链路 |
| Agent 体系 | 自治规划循环 | 全部为单次 LLM 调用 | **实质差距大** |
| 报告生成 | 统一 ReportDocument → 多格式 | 多数直接生成字符串 | 接入不统一 |
| 任务持久化 | 统一任务表/运行账本 | review 独立 SQLite，其余内存 | 重启丢状态 |
| 规则管理 | 统一规则引擎+版本控制 | 多种机制并存，无版本 | **无版本管理** |
| 测试案例 | 统一案例集+强断言 | 前后端两套，断言弱 | **覆盖率不足** |
| 前端入口 | 一套统一测试入口 | 多个专用按钮并存 | **行为不一致** |

---

> **审计证据索引**（关键代码定位）：
> - CN Flow system prompt 错误：`backend/common/llm/module_generator.py:55-60`
> - Pipeline repair 不阻断：`backend/common/workflow/pipeline.py:201-240`
> - 引用正文断链：`backend/domains/cn/security_assessment/report_renderer.py:370-412`
> - 产物授权回退（已修复）：`backend/api/v1/endpoints/artifacts.py`
> - 哈希确定性（已修复）：`backend/common/rag/embedding.py:38-57`
> - BCR/DPIA/TIA payload 构建失败：`frontend/src/components/workspace/ModuleRunPanel.tsx:802-1000`
> - 案例 Schema 漂移：`frontend/src/lib/dev-test-cases.ts:1-17`
> - 执行流空值：`frontend/src/components/workspace/RunTranscript.tsx:25-97`
> - 风险等级冲突：安全评估 2026-08-05 运行产物截图
> - 得理探测失败：设置页 2026-08-05 截图
> - 思诚资料重复哈希：`resources/new/` 三组 ZIP 解包验证

> **标注说明**：标记"已修复"的项目指在 2026-07-22 批次（提交 `0ad52ff`、`803c073`、`d97ba7e`、`7fd8489` 等）中已完成代码修复并通过自动化测试验证；"未完成边界"项目指代码已实现但未到达全平台/真实环境验证或存在仍未解决的缺口。
