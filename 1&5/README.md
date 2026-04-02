# AI4Law Backend

AI4Law 当前已完成两个后端模块的可运行 MVP：

- 模块①：合规路径诊断
  - 已升级为“结构化问卷 + 业务数据合规自画像（草案）+ 规则评估 + 路径分流”
- 模块⑤：文档智能审查
  - 已升级为“双模式合同审查平台”
  - `REPORT`：输出标准化审查报告
  - `REDLINE`：输出修订版合同与结构化差异

项目保持 `FastAPI + 分层 Service + SQLite/本地存储 + 可替换 AI/RAG 适配层` 的总体原理不变。模块①仍以规则为主判定，模块⑤仍以条款级分析为核心底座。

## 当前完成情况

### 模块①

- 诊断会话创建
- 结构化问卷提交
- 《业务数据合规自画像（草案）》生成
- 风险等级与路径评估
- HTML/PDF 评估报告生成
- 通向模块②/③的完整 handoff
- 旧版 `answers` 接口兼容映射

### 模块⑤

- 双模式审查任务创建
- `docx/pdf` 上传与文本提取
- 条款切分与附录识别
- 条款分类
- 条款级问题识别
- 风险聚合与总体评级
- `REPORT` 模式：生成《数据出境合同合规审查报告》
- `REDLINE` 模式：生成修订版合同 `.docx`
- 差异数据输出
- WebSocket 进度推送

### 共享基础设施

- FastAPI 应用入口
- SQLAlchemy 持久化
- SQLite 默认开发配置
- 本地上传文件存储
- 本地 inline 任务调度
- Pydantic 接口契约
- 得理法搜增强检索适配层

## 当前未完成项

- 模块②、③、④业务本体尚未落地
- OCR 扫描件、英文合同、多法域审查尚未实现
- 腾讯元宝 / 元器工作流尚未正式接入
- Celery / Redis / 对象存储 / JWT / RBAC 尚未接入
- Word 原生“修订痕迹”级别的 redline 仍属于后续增强项

## 目录结构

```text
backend/
  api/                 FastAPI 路由
  core/                配置、数据库、依赖注入
  data/                规则与本地知识数据
  models/              ORM 模型
  repositories/        仓储层
  schemas/             Pydantic 契约
  services/            业务服务与外部适配
tests/                 测试
pyproject.toml         依赖与项目配置
.env.example           环境变量示例
pipeline.md            产品流程说明
architecture.md        架构设计说明
principle.md           原理说明
```

## 环境变量

- `AI4LAW_DELILEGAL_APP_ID`
- `AI4LAW_DELILEGAL_SECRET`
- `AI4LAW_DELILEGAL_BASE_URL`

示例见 [`.env.example`](C:\Users\sataxisama\Desktop\agent individual\AI4law\.env.example)。

## 本地运行

推荐使用 Python 3.11+。

```bash
pip install -e .[dev]
uvicorn backend.app:create_app --factory --reload
```

健康检查：

```bash
GET /health
```

## 测试

```bash
python -m pytest -q
```

当前测试结果：

- `8 passed`

## 已实现接口

### 通用

- `GET /health`

### 模块①：合规路径诊断

- `POST /api/v1/diagnosis/sessions`
- `PUT /api/v1/diagnosis/sessions/{session_id}/questionnaire`
- `POST /api/v1/diagnosis/sessions/{session_id}/evaluate`
- `GET /api/v1/diagnosis/sessions/{session_id}/profile`
- `PUT /api/v1/diagnosis/sessions/{session_id}/answers`
- `GET /api/v1/diagnosis/sessions/{session_id}/result`
- `POST /api/v1/diagnosis/sessions/{session_id}/report`
- `GET /api/v1/diagnosis/sessions/{session_id}/context`
- `GET /api/v1/diagnosis/sessions/{session_id}/handoff/assessment`
- `GET /api/v1/diagnosis/sessions/{session_id}/handoff/scc`

### 模块⑤：双模式合同审查

- `POST /api/v1/review/tasks`
  - 请求体支持：
  - `review_mode`
  - `contract_type`
  - `review_stance`
  - `custom_rule_text`
  - `custom_rule_ids`
- `POST /api/v1/review/tasks/{task_id}/files`
- `POST /api/v1/review/tasks/{task_id}/analyze`
- `GET /api/v1/review/tasks/{task_id}/status`
- `GET /api/v1/review/tasks/{task_id}/issues`
- `GET /api/v1/review/tasks/{task_id}/report`
  - 仅 `REPORT` 模式可用
- `GET /api/v1/review/tasks/{task_id}/revised-contract`
  - 仅 `REDLINE` 模式可用
- `GET /api/v1/review/tasks/{task_id}/diff`
- `WS /api/v1/review/ws/tasks/{task_id}`

## 关键数据对象

### 模块①

- `ComplianceQuestionnaire`
- `ComplianceProfileDraft`
- `RuleHit`
- `RuleEvaluationResult`
- `DiagnosisAssessmentReport`
- `AssessmentHandoffResponse`
- `SCCHandoffResponse`

### 模块⑤

- `ReviewMode`
- `ContractType`
- `ReviewStance`
- `ReviewWorkspace`
- `Clause`
- `ClassifiedClause`
- `ReviewIssue`
- `AggregatedReview`
- `ReviewReport`
- `RevisionInstruction`
- `RevisedClause`
- `RevisionDiffItem`
- `RevisedContractResponse`

## 模块⑤实现原则

- 不把整份合同一次性丢给模型做黑盒改写
- 先切分条款，再做分类、审查、聚合
- `REPORT` 与 `REDLINE` 共享同一套解析和问题识别底座
- 审查立场和自定义规则进入后端审查逻辑，不只是前端展示字段
- 修订版合同以“定向补强与重组”为主，不做无约束全文重写

## 交付建议

如果要提交当前阶段成果，建议至少保留：

- `backend/`
- `tests/`
- `pyproject.toml`
- `README.md`
- `.env.example`
