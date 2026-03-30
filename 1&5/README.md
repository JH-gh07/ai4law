# AI4Law Backend

AI4Law 当前已完成两个后端模块的 MVP：

- 模块①：合规路径诊断（问卷诊断 + 自画像 + 风险评估）
- 模块⑤：文档智能审查

并已补齐模块①流向模块②和模块③的衔接接口，以及外部法律检索增强层的环境变量接入。

## 当前项目状态

### 已完成

- 模块①完整后端闭环
  - 诊断会话创建
  - 结构化问卷提交
  - 《业务数据合规自画像（草案）》生成
  - 规则表驱动的风险等级评估
  - 合规路径判定
  - 评估摘要与报告预览生成
  - HTML/PDF 诊断评估报告生成
  - 通用上下文查询
  - 流向模块②安全评估的完整 handoff 接口
  - 流向模块③认证/标准合同路径的完整 handoff 接口
  - 旧版 `answers` 接口兼容映射到新版问卷流程

- 模块⑤完整后端闭环
  - 审查任务创建
  - `docx/pdf` 上传
  - 文本提取
  - 条款切分
  - 条款分类
  - 规则审查
  - 问题聚合
  - docx 审查报告生成
  - 状态、问题列表、报告查询
  - WebSocket 进度推送入口

- 共享基础设施
  - FastAPI 应用入口
  - SQLAlchemy 持久化
  - SQLite 默认开发配置
  - 本地文件存储
  - 本地 inline 任务调度
  - Pydantic 契约模型
  - 单元测试与集成测试

- 外部检索增强
  - 已接入得理法搜 HTTP 适配层
  - 通过环境变量读取 `APP_ID` 和 `SECRET`
- 模块①评估引用、模块⑤法规引用可自动尝试远程补充
  - 远程调用失败时自动回退到本地规则库，不影响主流程

### 尚未完成

- 模块②、③、④业务本身尚未实现
- 腾讯元宝、腾讯元器、得理 API 的更深层工作流编排尚未实现
- OCR 扫描件、英文合同、多法域审查尚未实现
- RBAC、JWT、对象存储、Celery/Redis 尚未实现

## 目录结构

```text
backend/
  api/                 路由层
  core/                配置、数据库、依赖注入
  data/                本地规则与引用数据
  models/              ORM 模型
  repositories/        仓储层
  schemas/             Pydantic 契约
  services/            业务服务与外部适配
tests/                 测试
pyproject.toml         依赖与项目配置
.env.example           环境变量示例
```

## 环境变量

项目支持以下环境变量：

- `AI4LAW_DELILEGAL_APP_ID`
- `AI4LAW_DELILEGAL_SECRET`
- `AI4LAW_DELILEGAL_BASE_URL`

代码默认从环境变量读取，不会把密钥写入仓库文件。

示例见：

- [.env.example](C:\Users\sataxisama\Desktop\agent individual\AI4law\.env.example)

你刚刚提供的密钥我已经写入当前用户环境变量，后续新开的终端可直接使用。

## 本地运行

建议使用 Python 3.11+，当前已验证 Python 3.13 可运行。

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

当前最新测试结果：

- `6 passed`

## 已实现接口

### 通用

- `GET /health`

### 模块①：合规路径诊断

- `POST /api/v1/diagnosis/sessions`
  - 创建诊断会话

- `PUT /api/v1/diagnosis/sessions/{session_id}/questionnaire`
  - 提交完整结构化问卷

- `POST /api/v1/diagnosis/sessions/{session_id}/evaluate`
  - 触发规则评估、自画像摘要生成和路径分流

- `GET /api/v1/diagnosis/sessions/{session_id}/profile`
  - 获取《业务数据合规自画像（草案）》

- `PUT /api/v1/diagnosis/sessions/{session_id}/answers`
  - 兼容旧版短问答接口，内部映射到新版问卷流程

- `GET /api/v1/diagnosis/sessions/{session_id}/result`
  - 获取问卷、自画像、评估结果与结果摘要

- `POST /api/v1/diagnosis/sessions/{session_id}/report`
  - 生成 HTML/PDF 数据合规诊断评估报告

- `GET /api/v1/diagnosis/sessions/{session_id}/context`
  - 获取通用诊断上下文

- `GET /api/v1/diagnosis/sessions/{session_id}/handoff/assessment`
  - 获取模块①流向模块②的安全评估 handoff 数据
  - 返回 `questionnaire`、`profile`、`evaluation`、`company_profile`、`prefill_form`

- `GET /api/v1/diagnosis/sessions/{session_id}/handoff/scc`
  - 获取模块①流向模块③的认证/标准合同 handoff 数据
  - 返回 `questionnaire`、`profile`、`evaluation`、`company_profile`、`prefill_form`

### 模块⑤：文档智能审查

- `POST /api/v1/review/tasks`
  - 创建审查任务

- `POST /api/v1/review/tasks/{task_id}/files`
  - 上传待审查文档

- `POST /api/v1/review/tasks/{task_id}/analyze`
  - 触发审查

- `GET /api/v1/review/tasks/{task_id}/status`
  - 查询任务状态和聚合摘要

- `GET /api/v1/review/tasks/{task_id}/issues`
  - 查询问题清单

- `GET /api/v1/review/tasks/{task_id}/report`
  - 查询 docx 报告元数据和聚合结果

- `WS /api/v1/review/ws/tasks/{task_id}`
  - 审查进度推送入口

## 关键数据对象

### 模块①

- `ComplianceQuestionnaire`
- `ComplianceProfileDraft`
- `RuleHit`
- `RuleEvaluationResult`
- `DiagnosisAssessmentReport`
- `DiagnosisAnswerSet`
- `DiagnosisResult`
- `DiagnosisContextResponse`
- `AssessmentHandoffResponse`
- `SCCHandoffResponse`
- `DiagnosisReportResponse`

### 模块⑤

- `Clause`
- `ClassifiedClause`
- `ReviewIssue`
- `AggregatedReview`
- `ReviewTaskStatusResponse`
- `ReviewReportResponse`

## 外部法律检索调用说明

得理法搜适配层位于：

- [legal_api_service.py](C:\Users\sataxisama\Desktop\agent individual\AI4law\backend\services\legal_api_service.py)

当前接入方式：

- 模块①在生成风险评估引用与诊断说明时，会尝试补充远程检索结果
- 模块⑤在按条款类型取法规依据时，会尝试补充远程检索结果
- 若密钥未配置、网络失败或返回格式不匹配，系统自动回退到本地规则库

## 交付建议

如果你要把当前后端作为阶段性交付上传，建议至少保留这些内容：

- `backend/`
- `pyproject.toml`
- `README.md`
- `.env.example`
- `tests/`

不建议上传本地临时目录、缓存目录、用户级依赖目录或密钥文件。
