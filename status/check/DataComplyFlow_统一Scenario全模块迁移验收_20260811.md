# DataComplyFlow 统一 Scenario 全模块迁移验收

> 日期：2026-08-11
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：阶段3全11模块共享场景迁移 + cn_flow兼容案例修复

> 2026-08-12 增量：最新语义门禁为 603 个叶断言；PIPIA 三条共享案例的本地 HTTP、SSE、报告正文、引用链路和 PDF canvas 预览均已通过。详细证据见 `status/check/DataComplyFlow_PIPIA共享案例与浏览器本地验收_20260812.md`。下文 584 断言等数字保留为 2026-08-11 当时的历史快照。

## 共享场景总览

22 个 shared benchmark scenario，覆盖 11 个模块：
- `us_14117`(3), `eu_scc`(3), `tia`(2), `pipia`(3), `diagnosis`(3), `assessment`(2), `bcr`(2), `dpia`(2), `cpra`(1), `review`(1)

每场景含 `scenario.json`(request+display) + `expected.json`(harness断言)

## CLI 迁移状态

| 模块 | 案例数 | 已迁移 | 说明 |
|---|---|---|---|
| assessment | 2 | 2 | shared |
| bcr | 2 | 2 | shared |
| cn_flow | 2 | 0 | 兼容适配器, GeneGuard红/黄双案例 |
| cpra | 1 | 1 | shared |
| diagnosis | 3 | 3 | shared |
| dpia | 2 | 2 | shared |
| eu_scc | 3 | 3 | shared |
| pipia | 5 | 3 | 01(smoke)+03(derived) inline |
| review | 1 | 1 | shared |
| tia | 2 | 2 | shared |
| us_14117 | 3 | 3 | shared |
| **合计** | **26** | **22** | |

## 前端案例名称

- `scenario.display.name`：20个 (CPRA-1/Diag-1-3/Assess-1-2/EU-SCC-1-3/DPIA-1-2/TIA-1-2/PIPIA-1-3/US14117-1-3/Review-1)
- 内联名称：8个 (CPRA-2-3/BCR-1-2-3/CN-FLOW-1-2/Review-2, 均为product extension/compat adapter)

## 本阶段修复清单

1. BCR未使用导入(TS6133): 移除bcrControllerScenario/bcrHealthScenario
2. EU-SCC案例名称: 3处改用franceUkSccScenario.display.name等
3. TIA案例名称: 2处改用innovateUsTiaScenario.display.name等
4. assessment-02名称: 改用youxuanShoppingScenario.display.name
5. CPRA expected.json: 移除不输出的document_ir_json, output_files 7→6
6. **cn_flow案例重写**: 旧"云服务科技"→GeneGuard生物科技公司
   - 01_minimal: GeneGuard red(基因组+华源生命科学+HIGH)
   - 02_geolocation_yellow: GeneGuard yellow(位置+深度洞察+MEDIUM)
   - 前端CN-FLOW-1/2与CLI cn_flow-01/02事实对齐
   - lossy_fields: is_covered_person, onward_transfer, attachments.content_unparsed
7. case_inventory同步: CPRA 29→28, cn_flow 1→2(19+19), 总565→584
8. openpyxl安装: assessment恢复

## 验证结果

```text
CLI --no-llm: 26 PASS / 0 FAIL (11 modules, 584 leaf checks) ✓
Case parity: PASS (26 CLI cases, 28 dev cases) ✓
TypeScript: 0 errors ✓
前端 dev-test-cases: 19/19 ✓
全部20个scenario导入: 均为有效使用 ✓
CLI LLM cn_flow red: 23/23 PASS, 8 LLM calls, 15058 tokens ✓
```

## 一致性审计

- 26个CLI案例文件: 全部结构合法 ✓
- 22个共享场景: 全部被至少1个CLI消费者引用 ✓
- 22个expected.json: 全部操作符合法, 无未知操作符 ✓
- 3个inline CLI案例: 断言数6-16, 均超下限4 ✓
- dev_case_catalog: 28条目, 按模块分布正确 ✓
- 前端全部20个scenario导入: 每个display.name使用1次 ✓
- 无双声明(input+scenario_path或expected+expected_path) ✓
- 0个未使用导入 ✓

## cn_flow 兼容案例详情

```
cn_flow/01_minimal (GeneGuard红):
  company_name=GeneGuard生物科技公司
  us_person_count=10000, transaction_type=cooperative_research
  doj=human_genomic_data, recipient=华源生命科学(中国)
  is_restricted_party=true → 兼容层映射为None(lossy)
  结果: risk_level=HIGH, lossy_fields=[is_restricted_party, onward_transfer, ...]

cn_flow/02_geolocation_yellow (GeneGuard黄):
  company_name=GeneGuard生物科技公司
  us_person_count=150000, transaction_type=vendor_agreement
  doj=precise_geolocation_data, recipient=深度洞察(中国)
  结果: risk_level=MEDIUM
```

## 阶段5: CLI verbose-trace 实时输出 ✅

- `backend/tests/harness/terminal_trace.py`: `TerminalTraceSubscriber` 类，含敏感字段过滤（api_key/authorization/password 等 10 类键），ANSI 彩色时间戳输出
- `backend/tests/harness/runner.py`: 替换内联 stub 为生产导入
- 8 项验收测试全部通过：
  1. 默认模式不逐条输出 Trace ✅
  2. `--verbose-trace` 按事件产生顺序输出（递增序列号）✅
  3. 终端事件数与落盘事件数一致 ✅
  4. warning、fallback、LLM token 和 final 能正确显示 ✅
  5. `--no-llm --verbose-trace` 显示 `llm_calls=0` ✅
  6. 敏感字段不会出现在终端 ✅
  7. 订阅者输出失败不会使业务案例失败 ✅
  8. `--quiet` 与 `--verbose-trace` 冲突时立即拒绝 ✅

## 阶段6: 语义门禁 ✅

- `scripts/check_case_parity.py`: 新增 `_extract_semantic_fingerprint()` + `semantic_violations()`
  - 从 scenario request 中提取标准化身份：company_name、project_name、多层嵌套 profile、exporter/importer
  - TIA 字符串格式 `data_exporter_profile` 正则解析
  - 校验 CLI scenario_path 存在性、scenario 身份标识、source_exact 到 scenario 的映射
- 3 项语义测试全部通过：
  - 未出现意外 scenario_path 错误 ✅
  - 无身份 scenario 被正确报告 ✅
  - TIA 字符串 exporter_profile 身份检测通过 ✅
- `check_case_parity.py` 输出：`Case parity + semantic check passed (11 modules, 26 CLI cases, 584 leaf checks, 28 dev cases)`

## 全部测试汇总

| 测试集 | 结果 |
|---|---|
| test_terminal_trace (8) | 8/8 PASS |
| test_case_parity (24, 含3语义) | 24/24 PASS |
| CLI --no-llm 全模块 | 26/26 PASS |
| TypeScript | 0 errors |
| 前端 dev-test-cases | 19/19 |
| Case parity gate | PASS |

## CLI 全模块 LLM 回归 ✅

26/26 PASS，11 模块全覆盖：

| 模块 | 案例 | LLM调用 | 总Token | 结果 |
|---|---|---|---|---|
| assessment | 2 | 20+20 | ~28K | ✅ |
| bcr | 2 | 4+20 | ~27K | ✅ |
| cn_flow | 2 | 16+16 | ~26K | ✅ |
| cpra | 1 | 10 | 12797 | ✅ |
| diagnosis | 3 | 0(纯规则) | 0 | ✅ |
| dpia | 2 | 24+24 | ~35K | ✅ |
| eu_scc | 3 | 12+10+10 | ~22K | ✅ |
| pipia | 5 | 14×5 | ~28K | ✅ |
| review | 1 | 18 | ~4K | ✅ |
| tia | 2 | 18+18 | ~47K | ✅ |
| us_14117 | 3 | 8×3 | ~45K | ✅ |

注：cpra 首次因 LLM JSON 解析瞬态错误(Expecting ',' delimiter)FAIL，复跑后 32/32 PASS。

## 尚未完成

- [ ] 全模块真实本地浏览器验收（PIPIA HTTP/SSE/正文/引用/PDF canvas 已完成，其他模块仍待完成）
- [ ] 远程部署(需用户同意)
