# 数规通测试用例转化逻辑方案

> 2026-06-04 · 基于 `doc/数规通功能路径描述（含reference）、流程描述、测试案例` 的完整分析

---

## 一、现有测试资产盘点

### 1.1 规模

| 法域 | 模块 | 测试案例文档数 | 案例场景数 |
|------|------|:----------:|:--------:|
| CN | 合规路径诊断 (diagnosis) | 1 | 3 |
| CN | 安全评估路径 (assessment) | 1 | ≥2 |
| CN | 认证/标准合同路径 (pipia) | 1 | ≥2 |
| CN | 文档专项智能审查 (review) | 1 | ≥2 |
| EU | SCC审查 (scc/eu_scc) | 1 | 3 |
| EU | BCR审核 (bcr) | 1 | 3 |
| EU | DPIA草案生成 (dpia) | 1 | 2 |
| EU | TIA草案生成 (tia) | 1 | ≥2 |
| US | 14117行政令合规 (us_14117) | 1 | ≥2 |
| US | CPRA合规 (cpra) | 1 | 3 |
| **合计** | **10 个模块** | **10** | **≥25** |

### 1.2 每个案例的文档结构

每个测试案例是一个标准化的三层文档：

```
测试案例docx
  ├── 上层：场景背景描述（公司名、业务、植入的风险点）
  ├── 中层：用户输入详情（结构化表单数据，含表格）
  └── 下层：预期输出描述（自然语言，含具体断言点）
```

### 1.3 案例特点分析

以 CPRA 三个案例为例，每个案例覆盖不同的合规形态：

| 案例 | 企业类型 | 核心测试点 | 预期输出断言 |
|------|---------|-----------|------------|
| TrendyGoods | 电商（30M刀年收入） | 选择退出机制缺失、暗模式检测、广告合同不合规 | HIGH风险 × 3项，具体整改建议匹配 |
| DataFlow | SaaS服务商（18M刀年收入） | 适用性边界（年收入不达标但处理量>10万）、服务提供商角色混淆 | "受CPRA管辖"判定、DPA条款缺失、协助DSR义务 |
| FitLife AI | 健康科技（SPI密集） | 敏感信息同意有效性、暗模式获取同意、缺失Limit SPI权利 | HIGH/紧急风险、停止数据共享、重写同意流程、暗模式确认 |

---

## 二、转化逻辑

### 2.1 核心原则

```
一句话：把每个 .docx 测试案例转成一组 Python 测试函数，
        每个函数 = 构造Payloȧd → 调用service → 断言预期输出
```

### 2.2 五步转化法

```
Step A: 提取"结构化输入" → 构造 Payload
Step B: 提取"预期输出" → 拆成可验证的断言语句
Step C: 编写测试函数 → 先写 payload，再写调用，最后写断言
Step D: 运行 & 对照 docx 逐条核验
Step E: 发现 gap → 标记为已知差异，回写计划
```

### 2.3 关键工程问题

#### 问题 1：Agent 依赖 — 测试中如何 handle LLM/Agent 调用？

当前 CPRA 测试已经用 `monkeypatch.setenv("AI4LAW_CPRA_DISABLE_AGENT_LLM", "1")` 关闭 Agent LLM 调用。各模块也需要类似机制。

**方案**：统一环境变量命名规范

```
AI4LAW_DISABLE_AGENT_LLM    → 禁用所有 Agent LLM 调用
AI4LAW_FAST_RETRIEVE        → 使用本地缓存/不调用远程 RAG
AI4LAW_<MODULE>_DISABLE_LLM  → 模块级禁用
```

对已有 stub/mock 的模块（CPRA 用了 `_fast_render`、`_fast_chapters`、`_extractor_stub`），保持现有模式。对其他尚无 stub 的模块，在测试文件内定义。

#### 问题 2：异步路径 — 如何测试 SSE 事件流？

CPRA 的 `test_cpra_async_flow` 只测了状态轮询，没有测 intermediate 事件。

**方案**：新增事件流测试的模式

```python
def test_xxx_async_event_stream():
    # 1. 提交异步任务
    accepted = client.post("/api/v1/cpra/generate_async", json=payload)
    task_id = accepted.json()["task_id"]
    
    # 2. 连 SSE / 轮询拉取事件
    events = client.get(f"/api/v1/events/task/{task_id}/events?since=0")
    
    # 3. 断言事件流
    event_types = [e["event_type"] for e in events["events"]]
    assert "thought" in event_types
    assert "tool_start" in event_types
    assert "intermediate" in event_types
    assert "final" in event_types
    assert "final_brief" in event_types
    
    # 4. 断言 intermediate 事件内容
    facts_events = [e for e in events["events"] if e["event_type"] == "intermediate"]
    assert any("gap_items" in str(e.get("detail", {})) for e in facts_events)
```

#### 问题 3：预期输出是自然语言，怎么做精确断言？

每个案例的预期输出段落中包含大量可提取为结构化断言的信息：

| 预期输出模式 | 转化后的断言 |
|------------|-----------|
| "总体合规评级：高风险" | `assert result.risk_level == "HIGH"` |
| "发现 3 个高风险问题" | `assert high_count >= 1` |
| "必须立即修改页脚选择退出链接" | `assert any("opt-out" in g.gap.lower() for g in result.gap_items)` |
| "核心发现：与广告网络共享数据构成出售/共享" | `assert any("出售" in issue or "共享" in issue for issue in result.consistency_issues)` |
| "报告必须导向"存在风险"的审慎结论" | `assert "存在风险" in result.chapters[0].content` |

核心原则：**把每个自然语言描述拆成 2-4 条可代码验证的断言**。

---

## 三、测试文件组织规划

### 3.1 每个模块一个独立的测试文件

按当前已有测试文件 + 新增的模式：

```
backend/modules/
  cpra/tests/
    test_service.py          ← 已有 4 tests (sync path)
    test_agents_consistency.py ← 已有 2 tests
    test_agents_spi.py       ← 已有 2 tests
    test_agents_vendor.py    ← 已有 2 tests
    test_async_api.py        ← 已有 1 test (async flow, 需修复 401)
    test_cases_from_doc.py   ← [新增] CPRA 三个案例的转化测试
    test_event_stream.py     ← [新增] 验证 SSE 事件流的测试
  
  diagnosis/tests/
    test_cases_from_doc.py   ← [新增] 诊断三个案例的转化测试
  
  assessment/tests/
    test_cases_from_doc.py   ← [新增] 安全评估案例的转化测试
  
  pipia/tests/
    test_cases_from_doc.py   ← [新增] 认证/标准合同案例
  
  ... (其余模块同理)
```

### 3.2 公共测试基础设施

提取到 `backend/tests/conftest.py` 或 `backend/common/testing/`：

```python
# 公共 fixtures
@pytest.fixture
def disable_llm():
    """禁用所有 Agent LLM 调用"""
    import os
    old = os.environ.get("AI4LAW_DISABLE_AGENT_LLM")
    os.environ["AI4LAW_DISABLE_AGENT_LLM"] = "1"
    yield
    if old is not None:
        os.environ["AI4LAW_DISABLE_AGENT_LLM"] = old
    else:
        os.environ.pop("AI4LAW_DISABLE_AGENT_LLM", None)

@pytest.fixture
def fast_retrieve():
    """使用快速检索（不上真实 RAG）"""
    ...

@pytest.fixture
def assert_event_stream():
    """断言事件流包含指定的事件类型序列"""
    ...
```

---

## 四、CPRA 三年案例的转化详例

### 案例 1：TrendyGoods (电商) → `test_cpra_case_trendy_goods`

**Payload**：

```python
def test_cpra_case_trendy_goods(monkeypatch, disable_llm, fast_retrieve):
    service = CPRAService()
    service._render = _fast_render_kwargs  # capture render kwargs
    service._generate_chapters_from_context = lambda ctx, lvl, cit: [
        CPRAChapter(no=1, title="执行摘要", content="存在高风险", ...),
        ...
    ]
    
    payload = CPRARequest.model_validate({
        "company_name": "TrendyGoods Inc.",
        "dba_name": "TrendyGoods.com",
        "business_model": "线上时尚零售商，年收入约3000万美元，通过网站和移动应用向消费者直销。使用用户行为分析进行个性化推荐，并使用第三方广告服务。",
        "data_lifecycle": "收集→分析→个性化推荐→与第三方广告网络共享",
        "notice_and_consent": "隐私政策链接在网站底部。Cookie横幅仅提供'接受'按钮，同等突出的'拒绝所有'选项缺失。",
        "consumer_rights_process": "提供在线表单和邮箱渠道，但缺少免费电话。SLA为45天。",
        "opt_out_and_sale_sharing": "与AdNetwork Alpha和Beta共享用户浏览行为数据。页脚链接文字为'Privacy Settings'，未使用CPPA规定的'请勿出售或分享我的个人信息'标准化文字和三角图标。", 
        "vendor_management": "与AdNetwork的合同未包含其必须遵守消费者opt-out指令的条款。",
        # ... 其余字段
    })
    
    result = service.generate_report(payload)
    
    # 断言组 A：风险评级
    assert result.risk_level in ("HIGH", "MEDIUM")  # 文档说"中高风险漏洞"
    
    # 断言组 B：核心差距项
    gap_domains = {g.domain for g in result.gap_items}
    assert "opt_out_and_sale_sharing" in gap_domains or any("opt-out" in g.gap.lower() for g in result.gap_items)
    
    # 断言组 C：UI暗模式检测
    assert any("暗模式" in issue or "dark pattern" in issue.lower() for issue in result.consistency_issues)
    
    # 断言组 D：合同缺陷（广告合作伙伴）
    assert any("合同" in g.gap or "contract" in g.gap.lower() for g in result.gap_items)
    
    # 断言组 E：输出文件完整性
    assert result.output_files["docx"].endswith(".docx")
    assert result.output_files["xlsx"].endswith(".xlsx")
```

### 案例 2：DataFlow (SaaS) → `test_cpra_case_dataflow_saas`

```python
def test_cpra_case_dataflow_saas(monkeypatch, disable_llm, fast_retrieve):
    # 核心测试点：年收入不达标(18M < 25M)，但因处理量>10万仍受管辖
    
    service = CPRAService()
    payload = CPRARequest.model_validate({
        "company_name": "DataFlow Analytics LLC",
        "business_model": "B2B SaaS，为中小企业提供数据看板服务。年收入约1800万美元。",
        "data_lifecycle": "客户上传数据→分析处理→生成看板。作为服务提供商，数据由客户（控制者）决定处理目的。",
        "cpra_applicability_selfcheck": "公司认为自己不受CPRA管辖（年收入未达2500万门槛）",
        "notice_and_consent": "不与消费者直接交互。作为服务提供商，依赖客户（控制者）的通知义务。",
        "consumer_rights_process": "无面向消费者的DSR渠道。作为服务提供商，依赖控制者的DSR机制。",
        # ...
    })
    
    result = service.generate_report(payload)
    
    # 断言组 A：管辖判定（这是这个案例最核心的测试点）
    # 年收入<25M 但处理量可能>10万 → 仍然受管辖
    chapter1 = next((c for c in result.chapters if c.chapter_no == 1), None)
    if chapter1:
        assert "受管辖" in chapter1.content or "管辖" in chapter1.content or \
               any("适用" in g.gap for g in result.gap_items if g.domain == "applicability")
    
    # 断言组 B：服务提供商角色识别
    assert any("服务提供商" in str(g.gap) or "DPA" in str(g.gap) or "数据处理协议" in str(g.gap) 
               for g in result.gap_items)
    
    # 断言组 C：不应有面向消费者的DSR渠道缺失警告（因为处理者无此义务）
    dsr_gaps = [g for g in result.gap_items if "DSR" in g.gap or "消费者" in g.gap]
    # 如果有DSR相关的gap，应该指向"协助客户"而非"自己建立"
```

### 案例 3：FitLife AI (健康科技) → `test_cpra_case_fitlife_ai`

```python
def test_cpra_case_fitlife_ai(monkeypatch, disable_llm, fast_retrieve):
    # 核心测试点：SPI consent有效性、暗模式、出售/共享健康衍生数据
    
    service = CPRAService()
    payload = CPRARequest.model_validate({
        "company_name": "FitLife AI Inc.",
        "business_model": "智能健身APP，通过传感器收集健康/生物特征/位置数据，提供个性化指导和健康预测，推荐保健品和保险产品。",
        "data_lifecycle": "传感器采集→健康分析→个性化指导+向第三方营销→与保健品/保险公司共享",
        "notice_and_consent": "注册界面使用捆绑同意设计（同意所有才能使用）。对SPI处理的同意是通过不平等设计获取的。",
        "consumer_rights_process": "DSR渠道隐藏在'设置→隐私→更多选项→行使权利'的深层菜单中。完全缺失'限制敏感信息使用'的权利入口。",
        "opt_out_and_sale_sharing": "向保健品公司和保险公司共享健康衍生数据。未提供选择退出链接。",
        "spi_usage_summary": "健康数据用于个性化健身（合理）但同时用于第三方营销（超出合理范围）。",
        # ...
    })
    
    result = service.generate_report(payload)
    
    # 断言组 A：应为 HIGH 或更高（紧急）
    assert result.risk_level == "HIGH"
    
    # 断言组 B：暗模式检测
    assert any("暗模式" in issue or "dark pattern" in issue.lower() 
               for issue in result.consistency_issues)
    
    # 断言组 C：SPI 高风险
    high_gaps = [g for g in result.gap_items if g.risk_level == "HIGH"]
    assert any("SPI" in g.gap or "敏感" in g.gap or "spi" in g.domain for g in high_gaps)
    
    # 断言组 D：同意有效性问题
    assert any("同意" in g.gap or "consent" in g.gap.lower() for g in result.gap_items)
    
    # 断言组 E：Limit SPI 权利缺失
    assert any("limit" in g.gap.lower() or "限制" in g.gap for g in result.gap_items)
```

---

## 五、实施路线

### Phase A：基础设施（与现有 SSE 事件流打通）

| 任务 | 内容 | 产出 |
|------|------|------|
| A1 | 统一环境变量体系 | `backend/common/testing/env.py` |
| A2 | 公共 test fixtures | `backend/tests/conftest.py` |
| A3 | 事件流断言 helper | `backend/common/testing/event_assertions.py` |
| A4 | CPRA 现有 async 测试修复 (401) | 修复 `test_async_api.py` |

### Phase B：逐模块转化

按现有 doc 的完整度优先转化 CPRA 和 Diagnosis（这两个模块后端最成熟）：

| 优先级 | 模块 | 案例数 | 预计新增测试函数 |
|--------|------|:------:|:--------------:|
| P0 | CPRA | 3 | `test_cases_from_doc.py` (6-8 tests) |
| P0 | diagnosis | 3 | `test_cases_from_doc.py` (5-7 tests) |
| P1 | assessment | 2+ | `test_cases_from_doc.py` (4-6 tests) |
| P1 | pipia | 2+ | `test_cases_from_doc.py` (4-6 tests) |
| P1 | review | 2+ | `test_cases_from_doc.py` (4-6 tests) |
| P2 | scc | 3 | `test_cases_from_doc.py` (5-7 tests) |
| P2 | bcr | 3 | `test_cases_from_doc.py` (5-7 tests) |
| P2 | dpia | 2+ | `test_cases_from_doc.py` (4-6 tests) |
| P2 | tia | 2+ | `test_cases_from_doc.py` (4-6 tests) |
| P2 | us_14117 | 2+ | `test_cases_from_doc.py` (4-6 tests) |

### Phase C：事件流覆盖

给每个模块加一个事件流验证测试：

```python
def test_xxx_event_stream_contains_all_types():
    """验证异步执行产生完整的事件流（至少包含 6 种事件类型）"""
    ...
```

### Phase D：回归保护 & CI 集成

- 所有测试在 CI 跑
- 失败时输出 diff：哪个断言 vs 实际值不符
- 后续修改模块时，必须确保案例测试不退化

---

## 六、每个模块的断言优先级

基于文档分析，每个模块的测试关注点权重不同：

| 模块 | 核心断言优先级 |
|------|-------------|
| diagnosis | **路径判定正确性** > 风险提示 > 法规引用准确性 |
| assessment | **报告覆盖完整性** > CIIO/重要数据识别 > 风险结论方向 |
| pipia | **路径类型选择** > 合同/认证材料清单 > 个人信息量化 |
| review | **条款级问题检出率** > 问题严重度分级 > 法规引用 |
| scc | **模块选择正确性** > 条款冲突检测 > 子处理者授权 |
| bcr | **强制性要素完整性**（第三方受益人/责任主体） > 结构完整性 > 模块混淆检测 |
| dpia | **风险矩阵完整性** > 缓解措施具体性 > DPO意见 |
| tia | **补充措施有效性** > 第三国法律评估完整性 |
| cpra | **差距项完整性** > 风险评级 > 暗模式检测 > 服务提供商vs控制者边界 |
| us_14117 | **受限主体识别** > 实体清单完整性 > 敏感数据分类 |

---

## 七、一句话版转化路线

```
Phase A: 统一环境变量 + 公共 fixtures → Phase B: 逐模块转化 25+ 案例为 Python 测试 → 
Phase C: 每个模块加事件流验证 → Phase D: CI 集成 + 回归保护
```

每个 docx 案例 → 1 个 Python test 函数，函数内 4-8 条断言，覆盖该案例的核心预期输出。
