# resources/new/ 完整处置方案

> 基于：Phase 0-1 完成，219 个文件已登记
> 目标：为每个文件明确最终去向和时间表
> 编制日期：2026-08-07

## 一、三类核心资料完整处置

### 1. 测试案例（56 个文件）

#### 1.1 种子案例（50 个 DOCX）

| 状态 | 数量 | 处置动作 | 目标位置 | 时间 |
|------|------|----------|----------|------|
| 无冲突 | 30 | 提取 → JSON 规范化 → 发布 | `benchmarks/datasets/seed-cases-v1/` | Phase 3a (3-5天) |
| 有冲突 | 20 | 隔离 → 等裁决 → 规范化/删除 | `benchmarks/datasets/seed-cases-v1/quarantined/` | Phase 2 裁决后 |

**详细动作：**
```bash
# 无冲突案例（30个）
for case in CN_case_{01..03,05} CN_case_{06..20} EU_case_{01..05,07..20} US_case_{01..10}; do
  - 提取 DOCX 中的输入场景、期望输出、评分标准
  - 写入 $case.input.json + $case.expected.json
  - 验证 JSON schema
  - 移动到 benchmarks/datasets/seed-cases-v1/$module_id/
done

# 冲突案例（20个）
CN_case_04, EU_case_06, EU_case_{11..15}, EU_case_{16..20} → quarantined/
- 保留原始 DOCX
- 写入 quarantine_reason.txt
- 等待 Phase 2 裁决
```

#### 1.2 参考材料（6 个）

| 文件 | 类型 | 处置动作 | 目标位置 | 时间 |
|------|------|----------|----------|------|
| LexEval 论文 | PDF | 移动到研究参考 | `resources/research/benchmarks/lexeval.pdf` | Phase 2 |
| LegalBench 论文 | PDF | 移动到研究参考 | `resources/research/benchmarks/legalbench.pdf` | Phase 2 |
| PLAWBENCH 论文 | PDF | 移动到研究参考 | `resources/research/benchmarks/plawbench.pdf` | Phase 2 |
| 测试分数汇总表 | XLSX | 转换为 CSV → 版本化 | `benchmarks/datasets/seed-cases-v1/scores_baseline.csv` | Phase 3a |
| 基准材料 × 2 | 其他 | 归档到研究目录 | `resources/research/benchmarks/` | Phase 2 |

---

### 2. 知识库_新法域PDF（51 个）

#### 2.1 按法域处置计划

| 法域 | PDF数 | v0.2 动作 | v1.0 目标 | 最终位置 |
|------|-------|-----------|-----------|----------|
| 新加坡 | 6 | ✅ 影子试点 | 生产晋级（需审批） | `resources/legal/sources/sg/` |
| 越南 | 6 | 📋 法律效力复核 | 候选 | `resources/legal/sources/vn/` (待定) |
| 日本 | 9 | 📋 法律效力复核 | 候选 | `resources/legal/sources/jp/` (待定) |
| 韩国 | 7 | 📋 法律效力复核 | 候选 | `resources/legal/sources/kr/` (待定) |
| 香港 | 7 | 📋 法律效力复核 | 候选 | `resources/legal/sources/hk/` (待定) |
| 澳门 | 3 | 📋 法律效力复核 | 候选 | `resources/legal/sources/mo/` (待定) |
| 台湾 | 5 | 📋 法律效力复核 | 候选 | `resources/legal/sources/tw/` (待定) |
| 马来西亚 | 8 | 📋 法律效力复核 | 候选 | `resources/legal/sources/my/` (待定) |

#### 2.2 新加坡影子试点详细路径（Phase 4）

```bash
# 输入：resources/new/知识库补充/新加坡/*.pdf (6个)
# 输出：影子索引 + 评测报告

1. 法律效力复核（需法律专家）
   - 验证 6 个 PDF 是否为现行有效版本
   - 确认官方来源 URL
   - 记录生效日期、修订历史
   - 输出：sg_legal_authority_checklist.csv

2. sources.csv 登记
   - 添加 6 条记录到 resources/legal/catalog/sources.csv
   - jurisdiction=sg, status=shadow_candidate
   
3. 解析与分块
   - 使用 IngestionPipeline 解析 6 个 PDF
   - 生成 sg_chunks_v1.jsonl
   - 验证条款定位准确率

4. 影子索引构建
   - 构建 legal_sg_shadow_v1 索引
   - 不修改生产索引别名
   
5. 检索评测
   - 准备 sg_retrieval_testset.json (20 查询)
   - 测量 Recall@5, Recall@10, 引用定位准确率
   
6. 回滚演练
   - 验证索引可以安全删除
   - 验证不影响 CN/EU/US 生产流量
```

#### 2.3 其余 7 个法域（45 个 PDF）

**处置策略：** 保留在 `resources/new/` 作为**候选资产**，不进入 v0.2 和 v1.0。

**后续路径：** 每个法域独立走"法律复核 → 试点 → 审批 → 生产"流程，作为 v1.1+ 的独立发布。

---

### 3. 需求文档（1 个）

| 文件 | 处置动作 | 输出 | 时间 |
|------|----------|------|------|
| 《数规通需求说明书》v0.1.0 | 1. 提取 10 个任务需求<br>2. 生成需求追溯矩阵<br>3. 与现有代码对齐分析 | `resources/new/prd-coverage-analysis.md`<br>`resources/new/requirement-traceability.csv` | Phase 2a |

**需求追溯矩阵示例：**
```csv
prd_section,requirement_text,spec_file,module_id,code_path,test_path,gold_case,coverage_status
2.1,合规路径诊断,任务1功能说明.docx,cn.transfer_diagnosis,backend/domains/cn/transfer_diagnosis,backend/tests/cn_diagnosis,CN_case_01,covered
2.2,安全评估,任务2功能说明.docx,cn.security_assessment,backend/domains/cn/security_assessment,backend/tests/cn_assessment,CN_case_06,covered
...
```

---

## 二、辅助材料完整处置

### 1. Reference 库（91 个文件）

#### 当前问题
- 与 `resources/legal/sources/` 重复
- 占用 46MB 空间
- 维护两份版本容易漂移

#### 处置方案

| 类型 | 数量 | 动作 | 时间 |
|------|------|------|------|
| 法律 PDF（已入库） | ~30 | 删除，指向 `resources/legal/sources/` | Phase 2 |
| 模板 DOCX（已入库） | ~10 | 删除，指向 `resources/templates/` | Phase 2 |
| 功能说明（重复） | ~10 | 保留根目录版本，删除 reference 副本 | Phase 2 |
| 其他支持文件 | ~41 | 逐个审查，保留唯一副本 | Phase 2 |

**去重脚本：**
```bash
# resources/new/dedup_reference_library.sh
# 1. 读取 decisions.v1.jsonl 中的 duplicate_of 字段
# 2. 验证 canonical 文件存在
# 3. 删除 reference 库副本
# 4. 生成去重报告
```

---

### 2. 目录索引（10 个 HTML/MD）

#### 处置方案

```
知识库补充/新加坡/新加坡相关法规目录.md
知识库补充/越南/越南相关法规目录.md
... (共 5 对)

→ 提取官方来源 URL 和生效日期
→ 合并到 resources/legal/catalog/sources.csv 的 official_url 字段
→ 删除 HTML（与 MD 内容相同）
→ 保留 MD 作为人类可读索引
→ 移动到 resources/legal/catalog/jurisdiction_indexes/
```

---

### 3. 噪音文件（6 个 .DS_Store）

**处置：** Phase 2 删除，不进入任何目标目录。

---

### 4. 其他（3 个）

| 文件 | 类型 | 处置 |
|------|------|------|
| 167、数据出境合规实务手册.pdf | 产品手册 | 移动到 `resources/manuals/` |
| 数据分级分类指南GBT+43697-2024.pdf | 国标 | 移动到 `resources/standards/` |
| 数据安全技术敏感个人信息处理安全要求GBT+45574-2025.pdf | 国标 | 移动到 `resources/standards/` |

---

## 三、完整处置时间表

| Phase | 文件处置动作 | 涉及文件数 | 工时 |
|-------|--------------|------------|------|
| Phase 2 | PRD 追溯 + Reference 去重 + 目录索引整合 + 其他归档 | 1 + 91 + 10 + 3 = 105 | 2-3 天 |
| Phase 3a | 30 个种子案例规范化 + 3 个论文归档 | 33 | 3-5 天 |
| Phase 4 | 新加坡 6 个 PDF 影子试点 | 6 | 5-7 天 |
| 待裁决后 | 20 个冲突案例处置 | 20 | 待定 |
| v1.0 后 | 其余 45 个 PDF 逐法域晋级 | 45 | 每法域 2-4 周 |

---

## 四、最终目录结构

```
resources/
├── legal/
│   ├── catalog/
│   │   ├── sources.csv                    ← 新增 SG 6条 + 目录索引信息
│   │   └── jurisdiction_indexes/         ← 新增：5 个法域的 MD 索引
│   └── sources/
│       └── sg/                            ← 新增：新加坡 6 个 PDF
├── templates/                             ← 不变
├── research/
│   └── benchmarks/                        ← 新增：3 个论文 PDF
├── manuals/                               ← 新增：实务手册
└── standards/                             ← 新增：2 个国标 PDF

benchmarks/
└── datasets/
    └── seed-cases-v1/
        ├── cn.transfer_diagnosis/         ← 新增：5 个案例 JSON
        ├── cn.security_assessment/        ← 新增：5 个案例 JSON
        ├── ... (共 10 个模块目录)
        ├── quarantined/                   ← 新增：20 个冲突案例 DOCX
        ├── scores_baseline.csv            ← 从 XLSX 转换
        └── manifest.json

resources/new/                             ← 保留作为接收隔离区
├── manifest.intake.v1.json               ← 不变
├── analysis.phase1.json                  ← 不变
├── decisions.v1.jsonl                    ← 追加去重决策
├── prd-coverage-analysis.md              ← 新增：PRD 覆盖度分析
├── requirement-traceability.csv          ← 新增：需求追溯矩阵
└── 知识库补充/                            ← 保留 45 个候选 PDF
    ├── 越南/ (6 PDF)
    ├── 日本/ (9 PDF)
    ├── 韩国/ (7 PDF)
    ├── 香港/ (7 PDF)
    ├── 澳门/ (3 PDF)
    ├── 台湾/ (5 PDF)
    └── 马来西亚/ (8 PDF)
```

---

## 五、验收标准

**Gate 2+ 验收清单：**

- [ ] 50 个种子案例：30 个已规范化，20 个已隔离并记录原因
- [ ] 3 个 Benchmark 论文已归档到 `resources/research/benchmarks/`
- [ ] 6 个新加坡 PDF 已完成影子试点，有评测报告
- [ ] 45 个其余法域 PDF 保留在 `resources/new/` 并标记 `candidate`
- [ ] 1 个 PRD 已完成需求追溯矩阵
- [ ] 91 个 Reference 库文件已去重，重复副本已删除
- [ ] 10 个目录索引信息已整合到 `sources.csv`
- [ ] 6 个噪音文件已删除
- [ ] 3 个其他文件已归档到正确目录
- [ ] `resources/new/` 仅保留 manifest、decisions、分析报告和候选 PDF

**最终文件计数：**
- 移出 `resources/new/`：174 个文件
- 保留 `resources/new/`：45 个候选 PDF + 3 个 manifest/分析文件 = 48 个

---

**这份方案明确了 219 个文件的全部去向。你同意吗？**
